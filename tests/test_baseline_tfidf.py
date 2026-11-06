"""Baseline TF-IDF com dados sintéticos mínimos, sem rede nem API."""
import pytest

pytest.importorskip("sklearn")
import joblib  # noqa: E402

from scripts import baseline_tfidf as b  # noqa: E402
from scripts.avaliar_classificacao import ler_paginas  # noqa: E402
from scripts.avaliar_segmentacao import ler_gabarito  # noqa: E402

CSV = """lote_id,pagina,inicio_documento,documento_id,tipo,qualidade,observacao
A,1,sim,a1,aso,boa,
A,2,nao,a1,aso,boa,
A,3,sim,a2,holerite,boa,
B,1,sim,b1,aso,boa,
B,2,sim,b2,holerite,media,
C,1,sim,c1,aso,boa,
C,2,sim,c2,holerite,boa,
"""
TEXTOS = {"aso": "atestado de saude ocupacional medico exame admissional apto",
          "holerite": "holerite recibo de pagamento salario proventos descontos inss liquido"}


def _textos(tipos_por_pagina):
    return {i + 1: f"{TEXTOS[t]} pagina {i}" for i, t in enumerate(tipos_por_pagina)}


@pytest.fixture
def docs(tmp_path):
    p = tmp_path / "a.csv"
    p.write_text(CSV, encoding="utf-8")
    g, pg = ler_gabarito(str(p)), ler_paginas(str(p))
    out = []
    for lote, tipos in (("A", ["aso", "aso", "holerite"]), ("B", ["aso", "holerite"]), ("C", ["aso", "holerite"])):
        for d in b.montar_documentos(g[lote], pg[lote], _textos(tipos)):
            out.append({**d, "lote": lote})
    return out


def test_montar_documentos_junta_paginas_e_trunca(docs):
    assert [(d["lote"], d["ini"], d["fim"], d["tipo"]) for d in docs][:2] == [("A", 1, 2, "aso"), ("A", 3, 3, "holerite")]
    assert docs[0]["texto"].count("atestado") == 2
    longo = b.montar_documentos([(1, 1)], {1: ("aso", "boa")}, {1: "x" * 9000})
    assert len(longo[0]["texto"]) == 6000


def test_treino_salva_e_avalia(docs, tmp_path):
    modelo = b.novo_pipeline().fit([d["texto"] for d in docs], [d["tipo"] for d in docs])
    joblib.dump(modelo, tmp_path / "m.joblib")
    previstos = list(joblib.load(tmp_path / "m.joblib").predict([d["texto"] for d in docs]))
    assert previstos == [d["tipo"] for d in docs]
    r = b.relatorio("teste", b.linhas_de(docs, previstos))
    assert r["f1_macro"] == 1.0 and r["acuracia"] == 1.0


def test_validacao_cruzada_agrupada_por_lote(docs):
    previstos = b.validacao_cruzada(docs, folds=3)
    assert len(previstos) == len(docs) and set(previstos) <= {"aso", "holerite"}
