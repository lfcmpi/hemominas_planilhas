"""Processamento em lote de multiplos PDFs."""

import os
import tempfile
from dataclasses import dataclass, field

from src.field_mapper import LinhaPlanilha, mapear_comprovantes
from src.pdf_extractor import Comprovante, extrair_pdf


@dataclass
class BatchFileStatus:
    filename: str
    status: str  # "queued" | "processing" | "done" | "error"
    comprovante_count: int | None = None
    bolsa_count: int | None = None
    error_message: str | None = None
    linhas: list[LinhaPlanilha] = field(default_factory=list)
    comprovantes: list[Comprovante] = field(default_factory=list)
    comprovante_nums: str = ""


def processar_lote(files) -> dict:
    """Processa lista de FileStorage PDFs, retornando status por arquivo.

    Cada arquivo e processado independentemente — erro em um nao bloqueia os demais.
    """
    results = []
    all_linhas = []

    for file_obj in files:
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                file_obj.save(tmp.name)
                tmp_path = tmp.name

            comprovantes = extrair_pdf(tmp_path)

            if not comprovantes:
                results.append(BatchFileStatus(
                    filename=file_obj.filename,
                    status="error",
                    error_message="Nenhum comprovante encontrado no PDF.",
                ))
                continue

            linhas = mapear_comprovantes(comprovantes, tolerante=True)
            comp_nums = ",".join(c.numero for c in comprovantes if c.numero)

            file_status = BatchFileStatus(
                filename=file_obj.filename,
                status="done",
                comprovante_count=len(comprovantes),
                bolsa_count=len(linhas),
                linhas=linhas,
                comprovantes=comprovantes,
                comprovante_nums=comp_nums,
            )
            results.append(file_status)
            all_linhas.extend(linhas)

        except Exception as e:
            results.append(BatchFileStatus(
                filename=file_obj.filename,
                status="error",
                error_message=str(e),
            ))
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)

    return {
        "files": results,
        "all_linhas": all_linhas,
        "summary": {
            "total_files": len(files),
            "success_files": sum(1 for r in results if r.status == "done"),
            "error_files": sum(1 for r in results if r.status == "error"),
            "total_bolsas": len(all_linhas),
        },
    }
