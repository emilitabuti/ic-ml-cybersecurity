#!/usr/bin/env python3
"""Audita resultados temporais e documentos finais sem acessar dados brutos."""

from __future__ import annotations

import csv
from datetime import datetime
from hashlib import sha256
from html import unescape
import json
from pathlib import Path
import re
from typing import Any
from zipfile import ZipFile

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
DOC_DIR = ROOT / "docs/emili/relatorio-final"
REPORTS = ROOT / "ml-pipeline/reports_temporal/unsw"
FINAL_DIR = REPORTS / "final_evaluation"
TABLES_DIR = REPORTS / "tables"

PROTOCOL = REPORTS / "protocol.json"
FINAL_METRICS = REPORTS / "final_test_metrics.json"
EXECUTION_MANIFEST = FINAL_DIR / "execution_manifest.json"
ARTIFACT_MANIFEST = FINAL_DIR / "artifact_manifest.json"
API_VALIDATION = FINAL_DIR / "api_validation.json"
TABLES_MANIFEST = TABLES_DIR / "tables_manifest.json"
MODEL_ARTIFACT = ROOT / "ml-pipeline/models/model_rf_temporal_v2.pkl"

SOURCE_MD = DOC_DIR / "relatorio-final-emili.md"
REPORT_DOCX = DOC_DIR / "Relatorio-Final-IC-Emili-Vieira-Tabuti.docx"
REPORT_PDF = DOC_DIR / "Relatorio-Final-IC-Emili-Vieira-Tabuti.pdf"
SUMMARY_DOCX = DOC_DIR / "Resumo-Estendido-Emili-Vieira-Tabuti.docx"
SUMMARY_PDF = DOC_DIR / "Resumo-Estendido-Emili-Vieira-Tabuti.pdf"
EXECUTION_LOG = DOC_DIR / "log-execucao.md"
PROTOCOL_DOC = DOC_DIR / "protocolo-metodologico.md"

OUTPUT_JSON = DOC_DIR / "auditoria-final.json"
OUTPUT_MD = DOC_DIR / "auditoria-final.md"


def file_hash(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def docx_text(path: Path) -> str:
    with ZipFile(path) as archive:
        xml = archive.read("word/document.xml").decode("utf-8")
    return unescape(" ".join(re.findall(r"<w:t(?: [^>]*)?>(.*?)</w:t>", xml)))


def pdf_text(path: Path) -> tuple[str, int, list[tuple[float, float]]]:
    reader = PdfReader(path)
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    sizes = sorted(
        {
            (
                round(float(page.mediabox.width), 1),
                round(float(page.mediabox.height), 1),
            )
            for page in reader.pages
        }
    )
    return text, len(reader.pages), sizes


def word_count(text: str) -> int:
    plain = re.sub(r"[*`]", "", text)
    return len(re.findall(r"\b[\wÀ-ÿ][\wÀ-ÿ'–-]*\b", plain))


def bool_csv(value: str) -> bool:
    return value.strip().lower() == "true"


def close(left: Any, right: Any, tolerance: float = 1e-12) -> bool:
    return abs(float(left) - float(right)) <= tolerance


checks: list[dict[str, Any]] = []


def check(name: str, condition: bool, evidence: Any) -> None:
    checks.append(
        {
            "name": name,
            "status": "passed" if condition else "failed",
            "evidence": evidence,
        }
    )


def audit_sidecars() -> None:
    targets = [
        PROTOCOL,
        FINAL_METRICS,
        EXECUTION_MANIFEST,
        ARTIFACT_MANIFEST,
        API_VALIDATION,
        TABLES_MANIFEST,
        MODEL_ARTIFACT,
    ]
    for target in targets:
        sidecar = target.with_name(target.name + ".sha256")
        parts = sidecar.read_text(encoding="utf-8").split()
        actual = file_hash(target)
        check(
            f"sidecar:{target.relative_to(ROOT)}",
            len(parts) >= 2 and parts[0] == actual and parts[-1] == target.name,
            {"actual": actual, "recorded": parts[0], "filename": parts[-1]},
        )


def audit_manifests() -> tuple[dict[str, Any], dict[str, Any]]:
    protocol = load_json(PROTOCOL)
    final = load_json(FINAL_METRICS)
    execution = load_json(EXECUTION_MANIFEST)
    artifact = load_json(ARTIFACT_MANIFEST)
    api = load_json(API_VALIDATION)
    tables = load_json(TABLES_MANIFEST)

    protocol_hash = file_hash(PROTOCOL)
    final_hash = file_hash(FINAL_METRICS)
    model_hash = file_hash(MODEL_ARTIFACT)

    check(
        "encadeamento:protocolo",
        final["protocol_sha256"] == protocol_hash
        and execution["protocol_sha256"] == protocol_hash
        and artifact["protocol_sha256"] == protocol_hash,
        protocol_hash,
    )
    check(
        "encadeamento:métricas_finais",
        execution["final_summary_sha256"] == final_hash
        and artifact["final_metrics_sha256"] == final_hash
        and tables["source_final_metrics_sha256"] == final_hash,
        final_hash,
    )
    check(
        "encadeamento:artefato",
        artifact["artifact_sha256"] == model_hash
        and api["artifact_sha256"] == model_hash
        and artifact["artifact_size_bytes"] == MODEL_ARTIFACT.stat().st_size,
        {"sha256": model_hash, "bytes": MODEL_ARTIFACT.stat().st_size},
    )
    check(
        "política:teste_fechado",
        final["test_raw_reads"] == 1
        and final["test_evaluation_runs"] == 1
        and final["selection_or_tuning_on_test"] is False
        and execution["test_policy"]["raw_test_reads"] == 1
        and execution["test_policy"]["test_evaluation_runs"] == 1
        and execution["test_policy"]["selection_or_tuning_on_test"] is False
        and execution["test_policy"]["rerun_authorized"] is False
        and tables["test_reopened"] is False
        and artifact["test_reopened"] is False
        and api["test_reopened"] is False
        and api["validated_with_test_data"] is False,
        {
            "raw_reads": final["test_raw_reads"],
            "evaluation_runs": final["test_evaluation_runs"],
            "selection_or_tuning_on_test": final["selection_or_tuning_on_test"],
        },
    )
    check(
        "configuração:vencedor",
        protocol["overall_selected_configuration"]
        == {
            "algorithm": "random_forest",
            "variant": "top_30",
            "top_n": 30,
            "reason": "Maior F1 médio entre todas as configurações de desenvolvimento.",
        }
        and artifact["model_type"] == "random_forest"
        and artifact["selected_feature_count"] == 30
        and artifact["window_size"] == 10
        and artifact["model_input_count"] == 300,
        {
            "selected": protocol["overall_selected_configuration"],
            "artifact_input": artifact["model_input_count"],
        },
    )
    check(
        "ambiente:desvio_documentado",
        execution["status"] == "completed_with_disclosed_environment_deviation"
        and len(execution["deviations"]) == 2
        and execution["actual_execution_dependency_versions"]["scikit_learn"]
        == "1.9.0",
        execution["deviations"],
    )
    check(
        "api:inferência",
        api["status"] == "passed_exact_training_environment"
        and api["checks"]["prediction_matches_direct_artifact_inference"] is True
        and api["checks"]["predict_status"] == 200
        and api["checks"]["missing_feature_status"] == 422
        and api["checks"]["raw_feature_count"] == 43
        and api["checks"]["selected_feature_count"] == 30,
        api["checks"],
    )
    return protocol, final


def audit_tables(protocol: dict[str, Any], final: dict[str, Any]) -> None:
    manifest = load_json(TABLES_MANIFEST)
    for filename, metadata in manifest["artifacts"].items():
        path = TABLES_DIR / filename
        if filename.endswith(".csv"):
            rows = len(load_csv(path))
        else:
            rows = sum(
                1
                for line in path.read_text(encoding="utf-8").splitlines()
                if line.startswith("|")
            ) - 2
        check(
            f"tabela:{filename}:hash_e_linhas",
            file_hash(path) == metadata["sha256"] and rows == metadata["rows"],
            {"sha256": file_hash(path), "rows": rows},
        )

    metric_rows = {row["model"]: row for row in load_csv(TABLES_DIR / "final_model_metrics.csv")}
    metric_fields = ["auc_roc", "f1", "fpr", "pr_auc", "precision", "recall"]
    for model, result in final["results"].items():
        row = metric_rows[model]
        condition = (
            row["variant"] == result["variant"]
            and int(row["features"]) == result["feature_count"]
            and int(row["test_windows"]) == result["test_windows"]
            and all(close(row[field], result["metrics"][field]) for field in metric_fields)
        )
        check(f"conteúdo:métricas:{model}", condition, row)

    confusion_rows = {
        row["model"]: row for row in load_csv(TABLES_DIR / "confusion_matrices.csv")
    }
    for model, result in final["results"].items():
        row = confusion_rows[model]
        condition = all(
            int(row[field]) == result["confusion_matrix"][field]
            for field in ("tn", "fp", "fn", "tp")
        )
        check(f"conteúdo:matriz:{model}", condition, row)

    attack_rows = {
        (row["model"], row["attack_type"]): row
        for row in load_csv(TABLES_DIR / "attack_type_metrics.csv")
    }
    attack_ok = len(attack_rows) == 27
    for model, result in final["results"].items():
        for attack, attack_result in result["metrics_by_attack_type"].items():
            row = attack_rows[(model, attack)]
            attack_ok &= int(row["positive_examples"]) == attack_result["positive_examples"]
            attack_ok &= all(
                close(row[field], attack_result["metrics"][field])
                for field in metric_fields
            )
    check("conteúdo:métricas_por_ataque", attack_ok, {"rows": len(attack_rows)})

    feature_rows = load_csv(TABLES_DIR / "selected_features_final.csv")
    rf_names = final["results"]["random_forest"]["feature_names"]
    feature_ok = len(feature_rows) == 30
    for index, row in enumerate(feature_rows):
        feature_ok &= int(row["rank"]) == index + 1 and row["feature"] == rf_names[index]
        feature_ok &= bool_csv(row["used_by_decision_tree"]) == (index < 10)
        feature_ok &= bool_csv(row["used_by_lstm"]) == (index < 20)
        feature_ok &= bool_csv(row["used_by_random_forest"]) is True
    check("conteúdo:ranking_final", feature_ok, {"features": len(feature_rows)})

    development_rows = {
        row["model"]: row for row in load_csv(TABLES_DIR / "development_vs_test.csv")
    }
    development_ok = len(development_rows) == 3
    for model, selected in protocol["selected_configuration_by_algorithm"].items():
        row = development_rows[model]
        development_ok &= close(
            row["development_f1_mean"], selected["development_metrics"]["f1_mean"]
        )
        development_ok &= close(row["test_f1"], final["results"][model]["metrics"]["f1"])
        development_ok &= close(
            row["test_minus_development_f1"],
            final["results"][model]["metrics"]["f1"]
            - selected["development_metrics"]["f1_mean"],
        )
    check("conteúdo:desenvolvimento_vs_teste", development_ok, development_rows)


def audit_documents(final: dict[str, Any]) -> dict[str, Any]:
    source = SOURCE_MD.read_text(encoding="utf-8")
    report_docx = docx_text(REPORT_DOCX)
    summary_docx = docx_text(SUMMARY_DOCX)
    report_pdf, report_pages, report_sizes = pdf_text(REPORT_PDF)
    summary_pdf, summary_pages, summary_sizes = pdf_text(SUMMARY_PDF)
    documents = {
        "source_md": source,
        "report_docx": report_docx,
        "report_pdf": report_pdf,
        "summary_docx": summary_docx,
        "summary_pdf": summary_pdf,
    }

    required_fragments = [
        "0,9261",
        "0,9856",
        "0,8898",
        "0,8846",
        "306.701",
    ]
    for name, text in documents.items():
        check(
            f"documento:{name}:números_principais",
            all(fragment in text for fragment in required_fragments),
            required_fragments,
        )

    log_text = EXECUTION_LOG.read_text(encoding="utf-8")
    protocol_text = PROTOCOL_DOC.read_text(encoding="utf-8")
    document_paths = [REPORT_DOCX, REPORT_PDF, SUMMARY_DOCX, SUMMARY_PDF, SOURCE_MD]
    for path in document_paths:
        digest = file_hash(path)
        check(
            f"documento:{path.name}:hash_registrado",
            digest in log_text,
            digest,
        )

    check(
        "documento:protocolo_canônico",
        all(
            fragment in protocol_text
            for fragment in (
                "shuffle=False",
                "Random Forest `top_30`",
                "306.701 janelas",
                "F1 0,9261",
                "uma leitura bruta",
            )
        ),
        str(PROTOCOL_DOC.relative_to(ROOT)),
    )

    summary_start = source.index("# PARTE III — RESUMO ESTENDIDO")
    summary_end = source.index("[[LETTER_SECTION]]", summary_start)
    summary_source = source[summary_start:summary_end]
    summary_source = summary_source.split("\n", 1)[1]
    abstract_match = re.search(
        r"\*\*Resumo:\*\*(.+?)\*\*Palavras-chave:", summary_source, re.S
    )
    abstract_words = word_count(abstract_match.group(1)) if abstract_match else 0
    summary_words = word_count(summary_source)
    check(
        "documento:limites",
        report_pages <= 50
        and summary_pages == 5
        and abstract_words <= 250
        and 1000 <= summary_words <= 2000,
        {
            "report_pages": report_pages,
            "summary_pages": summary_pages,
            "abstract_words": abstract_words,
            "summary_words": summary_words,
            "report_page_sizes": report_sizes,
            "summary_page_sizes": summary_sizes,
        },
    )

    citation_numbers: set[int] = set()
    for start, end in re.findall(r"\[(\d+)(?:[–-](\d+))?\]", summary_source):
        first = int(start)
        last = int(end) if end else first
        citation_numbers.update(range(first, last + 1))
    reference_numbers = {
        int(value) for value in re.findall(r"^\[(\d+)\]\s", summary_source, re.M)
    }
    dois = re.findall(r"DOI:\s*(10\.\d{4,9}/[^\s.]+(?:\.[^\s.]+)*)", summary_source)
    check(
        "referências:resumo_numérico",
        citation_numbers == set(range(1, 8))
        and reference_numbers == set(range(1, 8))
        and len(dois) == 7,
        {
            "citations": sorted(citation_numbers),
            "references": sorted(reference_numbers),
            "doi_count": len(dois),
        },
    )
    bibliography = source[source.index("# REFERÊNCIAS BIBLIOGRÁFICAS") :]
    authors = [
        "ANKALAKI",
        "BERMAN",
        "BERTOLI",
        "CHAKIR",
        "ENNAJI",
        "HALBOUNI",
        "LE JEUNE",
        "TRAN",
        "SHAO",
        "YIN",
    ]
    check(
        "referências:relatório",
        all(author in bibliography for author in authors)
        and "REFERÊNCIAS BIBLIOGRÁFICAS" in report_docx
        and "REFERÊNCIAS BIBLIOGRÁFICAS" in report_pdf,
        authors,
    )

    todos = sorted(set(re.findall(r"TODO:[^*\n]+", source)))
    check("documento:lacunas_humanas", len(todos) == 5, todos)
    check(
        "documento:resultado_vencedor_exato",
        close(final["results"]["random_forest"]["metrics"]["f1"], 0.9260734838424082)
        and close(final["results"]["random_forest"]["metrics"]["pr_auc"], 0.9856091326917055),
        final["results"]["random_forest"]["metrics"],
    )
    return {
        "report_pages": report_pages,
        "summary_pages": summary_pages,
        "abstract_words": abstract_words,
        "summary_words": summary_words,
        "todos": todos,
    }


def write_outputs(document_summary: dict[str, Any]) -> None:
    failed = [item for item in checks if item["status"] == "failed"]
    files = [
        PROTOCOL,
        FINAL_METRICS,
        EXECUTION_MANIFEST,
        ARTIFACT_MANIFEST,
        API_VALIDATION,
        TABLES_MANIFEST,
        MODEL_ARTIFACT,
        SOURCE_MD,
        REPORT_DOCX,
        REPORT_PDF,
        SUMMARY_DOCX,
        SUMMARY_PDF,
        EXECUTION_LOG,
        PROTOCOL_DOC,
    ]
    result = {
        "schema_version": "1.0",
        "audit_type": "final_cross_document_integrity",
        "captured_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "status": "passed" if not failed else "failed",
        "read_only_sources": True,
        "raw_test_data_accessed": False,
        "test_reopened": False,
        "summary": {
            "checks_total": len(checks),
            "checks_passed": len(checks) - len(failed),
            "checks_failed": len(failed),
            **document_summary,
        },
        "files_audited": {
            str(path.relative_to(ROOT)): {
                "sha256": file_hash(path),
                "size_bytes": path.stat().st_size,
            }
            for path in files
        },
        "checks": checks,
    }
    OUTPUT_JSON.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    json_hash = file_hash(OUTPUT_JSON)
    OUTPUT_JSON.with_name(OUTPUT_JSON.name + ".sha256").write_text(
        f"{json_hash}  {OUTPUT_JSON.name}\n", encoding="utf-8"
    )

    lines = [
        "# Auditoria final dos resultados e documentos",
        "",
        f"**Status:** {'APROVADA' if not failed else 'REPROVADA'}  ",
        f"**Execução:** {result['captured_at']}  ",
        f"**Resultado completo:** `docs/emili/relatorio-final/{OUTPUT_JSON.name}`  ",
        f"**SHA-256 do JSON:** `{json_hash}`",
        "",
        "## Resultado",
        "",
        f"Foram aprovadas {len(checks) - len(failed)} de {len(checks)} verificações.",
        "A auditoria não acessou dados brutos nem reabriu o teste temporal.",
        "",
        "## Escopo verificado",
        "",
        "- hashes e encadeamento entre protocolo, métricas, manifestos, tabelas e modelo;",
        "- reprodução exata das métricas, matrizes, ranking e comparação desenvolvimento-teste;",
        "- números principais em Markdown, DOCX e PDF;",
        "- paginação, contagem de palavras, referências e campos humanos pendentes;",
        "- política de uma única leitura e avaliação do teste, sem ajuste posterior;",
        "- documentação do desvio de versões do ambiente final.",
        "",
        "## Documentos",
        "",
        f"- relatório: {document_summary['report_pages']} páginas;",
        f"- resumo estendido: {document_summary['summary_pages']} páginas e {document_summary['summary_words']} palavras;",
        f"- resumo introdutório: {document_summary['abstract_words']} palavras;",
        f"- lacunas humanas identificadas: {len(document_summary['todos'])}.",
        "",
        "## Pendências humanas",
        "",
    ]
    lines.extend(f"- {todo}" for todo in document_summary["todos"])
    if failed:
        lines.extend(["", "## Falhas", ""])
        lines.extend(f"- {item['name']}" for item in failed)
    OUTPUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    md_hash = file_hash(OUTPUT_MD)
    OUTPUT_MD.with_name(OUTPUT_MD.name + ".sha256").write_text(
        f"{md_hash}  {OUTPUT_MD.name}\n", encoding="utf-8"
    )
    if failed:
        raise SystemExit(f"Auditoria reprovada: {len(failed)} falha(s)")
    print(f"Auditoria aprovada: {len(checks)} verificações")
    print(OUTPUT_JSON)
    print(OUTPUT_MD)


def main() -> None:
    audit_sidecars()
    protocol, final = audit_manifests()
    audit_tables(protocol, final)
    document_summary = audit_documents(final)
    write_outputs(document_summary)


if __name__ == "__main__":
    main()
