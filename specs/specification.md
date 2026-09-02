---
okf_version: "0.2"
title: "Especificação de Specification"
description: "Contrato mínimo para documentos que declaram o schema semântico de um tipo OKF usado pelo ovigia-dados."
type: "specification"
target_type: "specification"
fields:
  target_type:
    type: string
    description: "Tipo OKF governado por esta especificação."
  fields:
    type: mapping
    description: "Campos semânticos declarados para o tipo."
---

# Especificação: `specification`

Documentos em `specs/` são conceitos OKF e constituem a camada declarativa de tipos do repositório. A existência de uma especificação deve ser exigida pelo `okf-parser --require-spec` para todo tipo governado.
