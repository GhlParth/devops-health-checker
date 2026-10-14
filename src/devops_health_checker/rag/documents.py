from dataclasses import dataclass
from pathlib import Path


@dataclass
class Document:
    content: str
    source: str
    category: str


def load_documents(
    knowledge_dir: str = "knowledge",
) -> list[Document]:
    root = Path(knowledge_dir)

    if not root.exists():
        return []

    documents = []

    for path in sorted(root.rglob("*.md")):
        content = path.read_text(
            encoding="utf-8"
        ).strip()

        if not content:
            continue

        relative_path = path.relative_to(root)

        category = (
            relative_path.parts[0]
            if len(relative_path.parts) > 1
            else "general"
        )

        documents.append(
            Document(
                content=content,
                source=str(relative_path),
                category=category,
            )
        )

    return documents