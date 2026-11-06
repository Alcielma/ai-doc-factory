"""Lógica de métricas, com um CSV mínimo criado aqui (não é o gabarito do gerador)."""
from scripts.avaliar_segmentacao import ler_gabarito, metricas, somar

CSV = """lote_id,pagina,inicio_documento,documento_id,tipo,qualidade,observacao
7,1,1,a,holerite,boa,
7,2,0,a,holerite,boa,verso_em_branco
7,3,1,b,holerite,boa,
7,4,1,c,aso,boa,
7,5,0,c,aso,boa,
"""


def test_ler_gabarito(tmp_path):
    p = tmp_path / "anotacoes.csv"
    p.write_text(CSV, encoding="utf-8")
    assert ler_gabarito(str(p)) == {"7": [(1, 2), (3, 3), (4, 5)]}


def test_metricas_perfeito_e_com_erros():
    real = [(1, 2), (3, 3), (4, 5)]
    assert metricas(real, real)["taxa_exatos"] == 1.0
    m = metricas(real, [(1, 3), (4, 5)])  # juntou os dois primeiros: perdeu a fronteira em 3
    assert (m["fronteiras_certas"], m["fronteiras_previstas"], m["fronteiras_reais"]) == (1, 1, 2)
    assert m["precisao"] == 1.0 and m["recall"] == 0.5
    assert m["exatos"] == 1 and abs(m["taxa_exatos"] - 1 / 3) < 1e-9
    m2 = metricas(real, [(1, 2), (3, 3), (4, 4), (5, 5)])  # dividiu o último
    assert m2["precisao"] == 2 / 3 and m2["recall"] == 1.0 and m2["exatos"] == 2


def test_somar():
    a = metricas([(1, 2), (3, 3)], [(1, 2), (3, 3)])
    b = metricas([(1, 1), (2, 2)], [(1, 2)])
    t = somar([a, b])
    assert (t["fronteiras_certas"], t["fronteiras_previstas"], t["fronteiras_reais"]) == (1, 1, 2)
    assert t["exatos"] == 2 and t["docs_reais"] == 4
