"""Lógica do avaliador de classificação, com CSV mínimo criado aqui (não é o gabarito do gerador)."""
from scripts.avaliar_classificacao import (avaliar, casar, documentos_reais, f1_macro, f1_por_classe, ler_paginas,
                                           matriz, por_qualidade, resumo)
from scripts.avaliar_segmentacao import ler_gabarito

CSV = """lote_id,pagina,inicio_documento,documento_id,tipo,qualidade,observacao
X,1,sim,a,holerite,boa,
X,2,nao,a,holerite,boa,
X,3,sim,b,aso,ruim,
X,4,sim,c,folha_ponto,media,
Y,1,sim,d,holerite,boa,
"""


def prev(ini, fim, probs, conf=0.9):
    return {"pagina_ini": ini, "pagina_fim": fim, "confianca": conf, "probabilidades": probs, "tipo": "x"}


def _reais(tmp_path, previstos_x):
    p = tmp_path / "a.csv"
    p.write_text(CSV, encoding="utf-8")
    g, pg = ler_gabarito(str(p)), ler_paginas(str(p))
    return [{**r, "previstos": previstos_x} for r in documentos_reais(g["X"], pg["X"])]


def test_documentos_reais_tipo_e_qualidade(tmp_path):
    reais = _reais(tmp_path, [])
    assert [(r["ini"], r["fim"], r["tipo"], r["qualidade"]) for r in reais] == [
        (1, 2, "holerite", "boa"), (3, 3, "aso", "ruim"), (4, 4, "folha_ponto", "media")]


def test_avaliar_segmentacao_exata_e_nenhum_como_desconhecido(tmp_path):
    previstos = [
        prev(1, 2, {"holerite": 1.0}),                       # exata e certa
        prev(3, 3, {"holerite": 0.7, "aso": 0.3}),           # exata, tipo errado
        prev(4, 4, {"nenhum_dos_anteriores": 1.0}),          # exata, "nenhum" = desconhecido
    ]
    linhas = avaliar(_reais(tmp_path, previstos))
    assert [(l["real"], l["previsto"], l["exata"]) for l in linhas] == [
        ("holerite", "holerite", True), ("aso", "holerite", True), ("folha_ponto", "desconhecido", True)]
    r = resumo(linhas)
    assert abs(r["acuracia"] - 1 / 3) < 1e-9
    assert r["por_classe"]["holerite"]["precisao"] == 0.5 and r["por_classe"]["holerite"]["recall"] == 1.0
    assert r["matriz"]["aso"]["holerite"] == 1 and r["matriz"]["folha_ponto"]["desconhecido"] == 1
    assert abs(r["f1_macro"] - (2 / 3) / 3) < 1e-9  # holerite 2/3, aso 0, folha_ponto 0


def test_segmentacao_divergente_usa_o_previsto_que_cobre_mais_paginas():
    real = {"ini": 1, "fim": 4, "tipo": "holerite", "qualidade": "boa"}
    previstos = [prev(1, 1, {"aso": 1.0}), prev(2, 4, {"holerite": 1.0})]
    assert casar(real, previstos) == ("holerite", False)  # 3 páginas contra 1; não é exata
    assert casar(real, [prev(9, 9, {"aso": 1.0})]) == ("sem_previsao", False)
    assert casar(real, [prev(1, 4, {"aso": 1.0}, conf=None)]) == ("sem_previsao", False)


def test_por_qualidade(tmp_path):
    linhas = avaliar(_reais(tmp_path, [prev(1, 2, {"holerite": 1.0}), prev(3, 3, {"aso": 1.0})]))
    assert por_qualidade(linhas) == {"boa": (1, 1), "media": (1, 0), "ruim": (1, 1)}


def test_filtro_por_lote_le_os_dois_lotes(tmp_path):
    p = tmp_path / "a.csv"
    p.write_text(CSV, encoding="utf-8")
    assert set(ler_paginas(str(p))) == {"X", "Y"} and set(ler_gabarito(str(p))) == {"X", "Y"}


def test_f1_macro_ignora_classes_sem_suporte():
    pc = f1_por_classe(matriz([("aso", "aso"), ("holerite", "aso")]))
    assert pc["recibo_ferias"]["suporte"] == 0
    assert abs(f1_macro(pc) - (2 / 3 + 0) / 2) < 1e-9  # aso: p=0.5 r=1 f1=2/3; holerite: 0
