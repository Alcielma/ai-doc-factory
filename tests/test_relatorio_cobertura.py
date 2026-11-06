"""Lógica do relatório, com CSV mínimo criado aqui (não é o gabarito do gerador)."""
from scripts.relatorio_cobertura import curva, ler_tipos_paginas, rotular, tipo_real

CSV = """lote_id,pagina,inicio_documento,documento_id,tipo,qualidade,observacao
7,1,1,a,holerite,boa,
7,2,0,a,holerite,boa,verso_em_branco
7,3,1,b,aso,boa,
7,4,1,c,folha_ponto,boa,
"""


def _doc(ini, fim, conf, probs, amb=False):
    return {"pagina_ini": ini, "pagina_fim": fim, "confianca": conf, "probabilidades": probs,
            "segmentacao_ambigua": amb}


def test_ler_e_tipo_real(tmp_path):
    p = tmp_path / "anotacoes.csv"
    p.write_text(CSV, encoding="utf-8")
    paginas = ler_tipos_paginas(str(p))["7"]
    assert tipo_real(paginas, 1, 2) == "holerite" and tipo_real(paginas, 3, 3) == "aso"
    assert tipo_real(paginas, 9, 9) is None


def test_rotular_e_curva(tmp_path):
    p = tmp_path / "anotacoes.csv"
    p.write_text(CSV, encoding="utf-8")
    paginas = ler_tipos_paginas(str(p))["7"]
    docs = [
        _doc(1, 2, 0.95, {"holerite": 1.0}),                       # certo, alta
        _doc(3, 3, 0.90, {"holerite": 0.8, "aso": 0.2}),           # errado, alta
        _doc(4, 4, 0.60, {"folha_ponto": 1.0}),                    # certo, média
        {"pagina_ini": 1, "pagina_fim": 1, "confianca": None},     # não classificado: ignorado
    ]
    itens, ignorados = rotular(paginas, docs)
    assert len(itens) == 3 and ignorados == 1
    c = {l["limiar"]: l for l in curva(itens, [0.5, 0.9, 0.99])}
    assert c[0.5]["automaticos"] == 3 and abs(c[0.5]["precisao_automatico"] - 2 / 3) < 1e-9
    assert c[0.9]["automaticos"] == 2 and c[0.9]["precisao_automatico"] == 0.5
    assert abs(c[0.9]["pct_revisao"] - 1 / 3) < 1e-9
    assert c[0.99]["automaticos"] == 0 and c[0.99]["precisao_automatico"] is None and c[0.99]["pct_revisao"] == 1.0


def test_ambiguo_e_sem_probabilidade_nao_ajudam():
    paginas = {1: "aso"}
    itens, _ = rotular(paginas, [_doc(1, 1, 0.99, {"aso": 1.0}, amb=True), _doc(1, 1, 0.99, {"aso": 0.0})])
    c = curva(itens, [0.5])[0]
    assert c["automaticos"] == 1 and c["corretos"] == 0  # o ambíguo vai para revisão; o sem sugestão erra


def test_nenhum_dos_anteriores_vai_para_revisao_em_qualquer_limiar():
    paginas = {1: "holerite", 2: "holerite"}
    probs = {"holerite": 0.0, "nenhum_dos_anteriores": 1.0}
    itens, _ = rotular(paginas, [_doc(1, 2, 1.0, probs)])  # confiança 1.0, mas sugestão é "nenhum"
    for l in curva(itens, [0.0, 0.5, 0.99]):
        assert l["automaticos"] == 0 and l["precisao_automatico"] is None and l["pct_revisao"] == 1.0


def test_tipo_desconhecido_e_baixa_confianca_seguem_o_roteamento_real():
    paginas = {1: "holerite", 2: "aso", 3: "aso"}
    docs = [
        {**_doc(1, 1, 0.99, {"holerite": 1.0}), "tipo": "desconhecido"},  # já roteado como desconhecido
        _doc(2, 2, 0.40, {"aso": 1.0}),                                     # abaixo de CONF_MIN: revisão
        _doc(3, 3, 0.95, {"aso": 1.0}),                                     # automático
    ]
    itens, _ = rotular(paginas, docs)
    c = curva(itens, [0.9])[0]
    assert c["automaticos"] == 1 and c["precisao_automatico"] == 1.0
