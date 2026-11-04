"""
Project ZRN — Main application
ByteBell Software

Flask server that ties together NFC, the Zermelo API, and the kiosk UI.
Run: python app.py
"""

import logging
import threading
from flask import Flask, render_template, jsonify, request
from zrn.utils.config import load_config
from zrn.api.zermelo import ZermeloClient
from zrn.nfc.reader import NFCReader
from zrn.nfc.mapping import UIDMapping

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

app = Flask(__name__, template_folder="zrn/ui/templates", static_folder="zrn/ui/static")

# Global state
config = load_config()
zermelo = ZermeloClient(school=config["school"], token=config["zermelo_token"])
nfc = NFCReader()
mapping = UIDMapping()

# Current session (student number shown on screen)
_current_student = {"leerlingnummer": None, "naam": "", "klas": ""}
_nfc_lock = threading.Lock()


# ── UI routes ──────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


# ── API routes ─────────────────────────────────────────────────────────────────

@app.route("/api/rooster/<leerlingnummer>")
def get_rooster(leerlingnummer: str):
    """Fetch the schedule for a given student number."""
    try:
        lessen = zermelo.get_schedule_today(leerlingnummer)
        student = zermelo.get_student_info(leerlingnummer)
        naam = " ".join(filter(None, [
            student.get("firstName", ""),
            student.get("prefix", ""),
            student.get("lastName", ""),
        ])) if student else ""
        # mainGroup isn't readable with a student-level token; fall back to the
        # group on the schedule itself (not every lesson has one, e.g. study
        # periods — use the first lesson that does).
        klas = student.get("mainGroup", "") if student else ""
        if not klas:
            klas = next((l.get("groep", "") for l in lessen if l.get("groep") not in (None, "", "—")), "")
        return jsonify({
            "ok": True,
            "leerlingnummer": leerlingnummer,
            "naam": naam,
            "klas": klas,
            "lessen": lessen,
        })
    except Exception as e:
        logger.error(f"Failed to fetch schedule: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/nfc/scan", methods=["POST"])
def nfc_scan():
    """
    Start an NFC scan (async). The frontend polls /api/nfc/status.
    """
    def _scan():
        with _nfc_lock:
            uid = nfc.read_uid(timeout=15)
            if uid:
                lnr = mapping.get_leerlingnummer(uid)
                _current_student["uid"] = uid
                _current_student["leerlingnummer"] = lnr
            else:
                _current_student["uid"] = None
                _current_student["leerlingnummer"] = None

    t = threading.Thread(target=_scan, daemon=True)
    t.start()
    return jsonify({"ok": True, "status": "scanning"})


@app.route("/api/nfc/status")
def nfc_status():
    """Return the current NFC scan session."""
    return jsonify(_current_student)


@app.route("/api/enrollment", methods=["POST"])
def enrollment():
    """Link a scanned UID to a student number."""
    data = request.json or {}
    uid = data.get("uid")
    lnr = data.get("leerlingnummer")
    naam = data.get("naam", "")
    klas = data.get("klas", "")
    if not uid or not lnr:
        return jsonify({"ok": False, "error": "uid and leerlingnummer are required"}), 400
    mapping.register(uid, lnr, naam, klas)
    return jsonify({"ok": True})


if __name__ == "__main__":
    port = config.get("port", 5000)
    debug = config.get("debug", False)
    logger.info(f"ZRN Terminal starting on port {port}")
    app.run(host="0.0.0.0", port=port, debug=debug)
