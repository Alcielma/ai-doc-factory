"""Avaliação da classificação por tipo (aceite do Goal 3): F1 macro e matriz de confusão, por documento.

Uso: python scripts/avaliar_classificacao.py anotacoes.csv [--api http://localhost:8000] [--lote ID_CSV:ID_API ...]

--lote ID_CSV:ID_API mapeia o lote do CSV para o id na API e, quando usado, restringe a avaliação a esses lotes.

Unidade: documento do gabarito (intervalos de `inicio_documento`). O tipo real é o mais frequente entre as
páginas dele, e a qualidade também.

Regra quando a segmentação diverge: o tipo previsto de um documento do gabarito é o tipo sugerido do documento
previsto que cobre MAIS páginas dele (empate: o primeiro). O tipo sugerido é o argmax das probabilidades do
classificador (`nenhum_dos_anteriores` e `desconhecido` contam como "desconhecido", que é erro para qualquer
tipo real), e não o campo `tipo`, que já passou por roteamento e correção humana. Se nenhum documento previsto
cobre o documento real, ou o que cobre não foi classificado, ele fica "sem previsão" e conta como erro.

Dois recortes são impressos: TODOS os documentos do gabarito e só os de SEGMENTAÇÃO EXATA (intervalo previsto
idêntico), mais a cobertura (quantos têm segmentação exata). F1 macro = média do F1 das classes com pelo menos
um documento real; precisão e recall de cada classe seguem a matriz. Por qualidade, só acurácia e contagens.

Os números dependem dos lotes: este script só mede, não valida o sistema.
"""
import argparse
import csv
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # permite importar app/ e scripts/ ao rodar direto
from app import config  # noqa: E402
from scripts.avaliar_segmentacao import ler_gabarito  # noqa: E402
from scripts.relatorio_cobertura import docs_da_api, tipo_sugerido  # noqa: E402

DESCONHECIDO = config.TIPO_DESCONHECIDO
SEM_PREVISAO = "sem_previsao"
COLUNAS = (*config.TIPOS, DESCONHECIDO, SEM_PREVISAO)


def ler_paginas(caminho: str) -> dict[str, dict[int, tuple[str, str]]]:
    """lote_id -> {pagina: (tipo, qualidade)}."""
    saida = defaultdict(dict)
    with open(caminho, newline="", encoding="utf-8") as f:
        for l in csv.DictReader(f):
            saida[l["lote_id"]][int(l["pagina"])] = (l["tipo"].strip(), l["qualidade"].strip())
    return dict(saida)


def _mais_frequente(valores: list[str]) -> str:
    cont = Counter(valores)
    return max(cont, key=lambda v: (cont[v], v))  # desempate estável


def documentos_reais(intervalos: list[tuple[int, int]], paginas: dict[int, tuple[str, str]]) -> list[dict]:
    docs = []
    for ini, fim in intervalos:
        pags = [paginas[p] for p in range(ini, fim + 1) if p in paginas]
        docs.append({"ini": ini, "fim": fim, "tipo": _mais_frequente([t for t, _ in pags]),
                     "qualidade": _mais_frequente([q for _, q in pags])})
    return docs


def casar(real: dict, previstos: list[dict]) -> tuple[str, bool]:
    """(tipo previsto, segmentação exata) para um documento real."""
    melhor, cobertura = None, 0
    for p in previstos:
        c = min(real["fim"], p["pagina_fim"]) - max(real["ini"], p["pagina_ini"]) + 1
        if c > cobertura:
            melhor, cobertura = p, c
    if melhor is None or melhor.get("confianca") is None:
        return SEM_PREVISAO, False
    exata = (melhor["pagina_ini"], melhor["pagina_fim"]) == (real["ini"], real["fim"])
    return tipo_sugerido(melhor) or SEM_PREVISAO, exata


def matriz(pares: list[tuple[str, str]]) -> dict[str, Counter]:
    m = defaultdict(Counter)
    for real, previsto in pares:
        m[real][previsto] += 1
    return m


def f1_por_classe(m: dict[str, Counter]) -> dict[str, dict]:
    saida = {}
    for tipo in config.TIPOS:
        suporte = sum(m[tipo].values()) if tipo in m else 0
        tp = m[tipo][tipo] if tipo in m else 0
        previstos = sum(m[r][tipo] for r in m)
        prec = tp / previstos if previstos else 0.0
        rec = tp / suporte if suporte else 0.0
        f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
        saida[tipo] = {"suporte": suporte, "precisao": prec, "recall": rec, "f1": f1}
    return saida


def f1_macro(por_classe: dict[str, dict]) -> float | None:
    f1s = [c["f1"] for c in por_classe.values() if c["suporte"] > 0]
    return sum(f1s) / len(f1s) if f1s else None


def avaliar(reais: list[dict]) -> list[dict]:
    """reais: documentos_reais(...) dos lotes avaliados, cada um com seus documentos previstos em ['previstos']."""
    linhas = []
    for r in reais:
        previsto, exata = casar(r, r["previstos"])
        linhas.append({"real": r["tipo"], "previsto": previsto, "exata": exata, "qualidade": r["qualidade"]})
    return linhas


def resumo(linhas: list[dict]) -> dict:
    m = matriz([(l["real"], l["previsto"]) for l in linhas])
    por_classe = f1_por_classe(m)
    corretos = sum(l["real"] == l["previsto"] for l in linhas)
    return {"n": len(linhas), "acuracia": corretos / len(linhas) if linhas else None, "matriz": m,
            "por_classe": por_classe, "f1_macro": f1_macro(por_classe)}


def por_qualidade(linhas: list[dict]) -> dict[str, tuple[int, int]]:
    q = defaultdict(lambda: [0, 0])
    for l in linhas:
        q[l["qualidade"]][0] += 1
        q[l["qualidade"]][1] += l["real"] == l["previsto"]
    return {k: tuple(v) for k, v in sorted(q.items())}


def _fmt(x: float | None) -> str:
    return "n/d" if x is None else f"{x:.3f}"


def imprimir(titulo: str, r: dict) -> None:
    print(f"\n== {titulo}: {r['n']} documentos | acurácia={_fmt(r['acuracia'])} | F1 macro={_fmt(r['f1_macro'])}")
    if not r["n"]:
        return
    print(f"{'tipo':<18}{'suporte':>8}{'precisão':>10}{'recall':>8}{'F1':>7}")
    for t, c in r["por_classe"].items():
        print(f"{t:<18}{c['suporte']:>8}{c['precisao']:>10.3f}{c['recall']:>8.3f}{c['f1']:>7.3f}")
    usadas = [c for c in COLUNAS if any(r["matriz"][real][c] for real in r["matriz"])]
    print("matriz de confusão (linhas = real, colunas = previsto):")
    print(f"{'':<18}" + "".join(f"{c[:11]:>12}" for c in usadas))
    for real in config.TIPOS:
        if real in r["matriz"]:
            print(f"{real:<18}" + "".join(f"{r['matriz'][real][c]:>12}" for c in usadas))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--api", default="http://localhost:8000")
    ap.add_argument("--lote", action="append", default=[], help="ID_CSV:ID_API (restringe aos lotes dados)")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    mapa = dict(x.split(":", 1) for x in args.lote)
    gabarito, paginas = ler_gabarito(args.csv), ler_paginas(args.csv)
    reais = []
    for lote in sorted(gabarito):
        if mapa and lote not in mapa:
            continue
        previstos = docs_da_api(args.api, mapa.get(lote, lote))
        for r in documentos_reais(gabarito[lote], paginas[lote]):
            reais.append({**r, "previstos": previstos})
    linhas = avaliar(reais)
    exatas = [l for l in linhas if l["exata"]]
    print(f"documentos do gabarito: {len(linhas)} | segmentação exata (cobertura): {len(exatas)}/{len(linhas)}")
    imprimir("TODOS os documentos do gabarito", resumo(linhas))
    imprimir("só segmentação exata", resumo(exatas))
    print("\npor qualidade (todos): " + " | ".join(
        f"{q}: {c}/{n} corretos" for q, (n, c) in por_qualidade(linhas).items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
