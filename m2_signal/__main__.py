"""Portable CLI. Every command is local and provider-disabled."""
import argparse
import json
from pathlib import Path

from .engine import analyze, backup_database, digest, ingest_export, restore_database


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    replay = sub.add_parser('replay')
    replay.add_argument('--source-dir', type=Path, required=True)
    replay.add_argument('--output', type=Path, required=True)
    replay.add_argument('--database', type=Path)
    replay.add_argument('--config', type=Path)
    calc = sub.add_parser('analyze')
    calc.add_argument('--database', type=Path, required=True)
    calc.add_argument('--release-id', required=True)
    calc.add_argument('--output', type=Path, required=True)
    for command in ('backup', 'restore'):
        s = sub.add_parser(command)
        s.add_argument('--source', type=Path, required=True)
        s.add_argument('--destination', type=Path, required=True)
    legacy = sub.add_parser('import-legacy-db')
    legacy.add_argument('--source', type=Path, required=True)
    legacy.add_argument('--output', type=Path, required=True)
    legacy.add_argument('--snapshot-date', required=True)
    args = parser.parse_args(argv)
    if args.command == 'replay':
        config = json.loads(args.config.read_text()) if args.config else None
        database = args.database or args.output/'signal.sqlite'
        receipt = ingest_export(database, args.source_dir, config)
        summary = analyze(database, receipt['release_id'], args.output)
        receipts = args.output/'ingest-receipts'
        receipts.mkdir(exist_ok=True)
        (receipts/(digest(receipt)+'.json')).write_text(json.dumps(receipt, indent=2, sort_keys=True)+'\n')
        print(json.dumps({'release_id': receipt['release_id'], 'population': summary['population'],
                          'new_immutable_records': receipt['new_immutable_records'], 'state': summary['stage_state']}, sort_keys=True))
    elif args.command == 'analyze':
        result = analyze(args.database, args.release_id, args.output)
        print(json.dumps({'release_id': result['release_id'], 'population': result['population']}, sort_keys=True))
    elif args.command == 'import-legacy-db':
        from .legacy import import_legacy_db
        print(json.dumps(import_legacy_db(args.source, args.output, args.snapshot_date), sort_keys=True))
    else:
        function = backup_database if args.command == 'backup' else restore_database
        print(json.dumps(function(args.source, args.destination), sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
