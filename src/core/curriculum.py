# src/core/curriculum.py

CURRICULUM = {
    1: {
        "fund_educacao_distancia": {
            "name": "Fundamentos de Educação a Distância",
            "area": "Interdisciplinar",
        },
        "fund_mat_elementar": {
            "name": "Fundamentos de Matemática Elementar",
            "area": "Matemática",
        },
        "introd_programacao": {
            "name": "Introdução à Programação",
            "area": "Computação",
        },
        "geometria_analitica": {
            "name": "Geometria Analítica",
            "area": "Matemática",
        },
        "fund_tec_educacional": {
            "name": "Fundamentos de Tecnologia Educacional",
            "area": "Interdisciplinar",
        },
    },
    2: {
        "calculo_1": {
            "name": "Cálculo I",
            "area": "Matemática",
        },
        "fisica_1": {
            "name": "Física I",
            "area": "Física",
        },
        "ciencia_tecnologia_sociedade": {
            "name": "Ciência, Tecnologia e Sociedade",
            "area": "Interdisciplinar",
        },
        "escrita_cientifica": {
            "name": "Escrita Científica",
            "area": "Interdisciplinar",
        },
        "quimica_geral": {
            "name": "Química Geral",
            "area": "Naturezas",
        },
    },
    3: {
        "algebra_linear": {
            "name": "Álgebra Linear",
            "area": "Matemática",
        },
        "atitude_empreendedora": {
            "name": "Atitude Empreendedora",
            "area": "empreendedorismo",
        },
        "calculo_2": {
            "name": "Cálculo II",
            "area": "Matemática",
        },
        "fisica_2": {
            "name": "Física II",
            "area": "Naturezas",
        },
        "politicas_publicas_ct": {
            "name": "Políticas Públicas de Ciência e Tecnologia",
            "area": "Interdisciplinar",
        },
    },
    4: {
        "calculo_3": {
            "name": "Calculo 3",
            "area": "Matemática",
        },
        "fisica_3": {
            "name": "Física 3",
            "area": "Naturezas",
        },
        "gestao_conhecimento": {
            "name": "Gestão do Conhecimento",
            "area": "Interdisciplinar",
        },
        "matematica_financeira": {
            "name": "Matemática Financeira",
            "area": "Matemática",
        },
        "probabilidade_estatistica": {
            "name": "Probabilidade e Estatística",
            "area": "Matemática",
        }
    },
    5: {
        "banco_dados": {
            "name": "Banco de Dados",
            "area": "Computação",
        },
        "calculo_numerico": {
            "name": "Cálculo Numérico",
            "area": "Matemática",
        },
        "gestao_projetos": {
            "name": "Gestão de Projetos",
            "area": "Interdisciplinar",
        },
        "optativa_1": {
            "name": "Optativa I",
            "area": "",
        },
        "plataforma_api": {
            "name": "Plataformas e APIs",
            "area": "Computação",
        }
    },
    6: {
        "analise_redes_sociais": {
            "name": "Análise de Redes Sociais",
            "area": "Interdisciplinar",
        },
        "ciencia_dados": {
            "name": "Ciência de Dados",
            "area": "Computação",
        },
        "inteligencia_negocios": {
            "name": "Inteligência de Negócios",
            "area": "Interdisciplinar",
        },
        "optativa_2": {
            "name": "Optativa II",
            "area": "",
        },
        "pesquisa_operacional": {
            "name": "Pesquisa Operacional",
            "area": "Computação",
        }
    }
}

def get_disciplines_for_semester(semester: int) -> dict:
    return CURRICULUM.get(int(semester), {})

def flatten_disciplines() -> dict:
    result = {}
    for sem, items in CURRICULUM.items():
        result.update(items)
    return result
