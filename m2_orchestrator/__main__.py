"""Local checkpoints, task exports, and explicit worker completion commands."""

import argparse
import json
import sys
from pathlib import Path

from .policy import BY_ID, policy
from .state import Controller, StateError


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run-dir", type=Path, default=Path(".local/m2-run"))
    sub = p.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init")
    init.add_argument("--config", type=Path, required=True)
    init.add_argument("--run-id", required=True)
    for name in ("status", "trace", "verify", "policy", "tasks"):
        sub.add_parser(name)
    start = sub.add_parser("begin")
    start.add_argument("stage", choices=BY_ID)
    start.add_argument("--actor", required=True)
    start.add_argument("--subject-hash")
    start.add_argument("--lease-seconds", type=int, default=900)
    finish = sub.add_parser("finish")
    finish.add_argument("stage", choices=BY_ID)
    finish.add_argument("--token", required=True)
    finish.add_argument("--artifact", action="append", required=True)
    finish.add_argument("--limitation", action="append", default=[])
    fail = sub.add_parser("fail")
    fail.add_argument("stage", choices=BY_ID)
    fail.add_argument("--token", required=True)
    fail.add_argument("--error", required=True)
    fail.add_argument("--state", choices=["FAIL", "BLOCKED_OWNER", "BLOCKED_EVIDENCE"], default="FAIL")
    recover = sub.add_parser("recover")
    recover.add_argument("stage", choices=BY_ID)
    approval = sub.add_parser("approve")
    approval.add_argument("--gate", required=True)
    approval.add_argument("--subject-hash", required=True)
    approval.add_argument("--actor", required=True)
    approval.add_argument("--expires", type=float, required=True)
    approval.add_argument("--revoke", action="store_true")
    args = p.parse_args(argv)
    if args.command == "policy":
        result = policy()
    else:
        c = Controller(args.run_dir)
        if args.command == "init":
            result = {"config_hash": c.init(args.run_id, json.loads(args.config.read_text()))}
        elif args.command == "status":
            result = c.status()
        elif args.command == "trace":
            result = c.trace()
        elif args.command == "verify":
            result = c.verify()
        elif args.command == "tasks":
            status = c.status()
            role_file = Path(__file__).parent.parent / "agents" / "m2-roles.json"
            roles = {r["role"]: r for r in json.loads(role_file.read_text())["roles"]}
            result = [{"run_id": status["run_id"], "config_hash": status["config_hash"], **row,
                       "task": BY_ID[row["id"]].__dict__,
                       "role_contract": roles[BY_ID[row["id"]].role],
                       "dispatch": "interactive specialist or authenticated server worker; no automatic model API",
                       "instructions": roles[BY_ID[row["id"]].role]["skill"]}
                      for row in status["stages"] if row["state"] not in {"PASS", "PASS_WITH_LIMITATIONS"}]
        elif args.command == "begin":
            result = c.begin(args.stage, args.actor, args.subject_hash, args.lease_seconds)
        elif args.command == "finish":
            result = c.finish(args.stage, args.token, args.artifact, "PASS_WITH_LIMITATIONS" if args.limitation else "PASS", args.limitation)
        elif args.command == "fail":
            c.fail(args.stage, args.token, args.error, args.state)
            result = c.status()
        elif args.command == "recover":
            c.recover(args.stage)
            result = c.status()
        elif args.command == "approve":
            c.approve(args.gate, args.subject_hash, args.actor, args.expires, args.revoke)
            result = {"approval_recorded": True, "external_action_performed": False}
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except (StateError, OSError, json.JSONDecodeError) as exc:
        # Never print raw provider responses, file bodies, or credentials.
        print(json.dumps({"state": "FAIL", "reason": str(exc) if isinstance(exc, StateError) else type(exc).__name__}), file=sys.stderr)
        raise SystemExit(2)

