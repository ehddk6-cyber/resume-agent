#!/usr/bin/env python3
"""임베딩 모델 업그레이드 마이그레이션 스크립트"""

import argparse
import json
import shutil
from pathlib import Path
from datetime import datetime

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from resume_agent.semantic_engine import SemanticSearchEngine


def migrate_embeddings(
    kb_path: str = "./kb",
    dry_run: bool = False,
    force: bool = False
):
    """임베딩 마이그레이션 실행"""
    kb_dir = Path(kb_path)
    index_file = kb_dir / "vector" / "index.json"
    backup_dir = kb_dir / "vector" / "backups"

    print(f"=== Embedding Migration ===")
    print(f"KB Path: {kb_path}")
    print(f"Dry Run: {dry_run}")

    if not index_file.exists():
        print("No existing index found. Nothing to migrate.")
        return

    with open(index_file, "r", encoding="utf-8") as f:
        index_data = json.load(f)

    old_dim = index_data.get("embedding_dimension", 384)
    print(f"Current dimension: {old_dim}")

    engine = SemanticSearchEngine()
    new_dim = engine._get_embedding_model().get_sentence_embedding_dimension()
    print(f"New dimension: {new_dim}")

    if old_dim == new_dim and not force:
        print("Dimensions match. No re-embedding needed.")
        return

    if not dry_run:
        backup_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = backup_dir / f"index_backup_{ts}_dim{old_dim}.json"
        shutil.copy(index_file, backup_file)
        print(f"Backup: {backup_file}")

    if dry_run:
        docs = len(index_data.get("documents", []))
        print(f"[DRY RUN] Would re-index {docs} documents")
    else:
        docs = [{"id": d["id"], "text": d["text"], "metadata": d.get("metadata", {})}
                for d in index_data.get("documents", [])]
        engine.index_documents(docs, persist=True)
        with open(index_file, "r", encoding="utf-8") as f:
            new_idx = json.load(f)
        print(f"Done. {len(new_idx.get('documents', []))} documents re-indexed.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--kb-path", default="./kb")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    migrate_embeddings(args.kb_path, args.dry_run, args.force)


if __name__ == "__main__":
    main()
