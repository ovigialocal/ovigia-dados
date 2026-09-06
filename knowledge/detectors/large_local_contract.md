---
okf_version: "0.2"
title: "Detector de Contratos Locais Relevantes (v1)"
description: "Identifica contratos federais de magnitude atípica em recortes municipais."
type: "detector"
detector_id: "large-local-contract"
edition_id: "porto-velho"
version: "1.0"
input_dataset: "contracts"
scope: "Porto Velho / RO"
baseline_policy: "12 a 24 meses de histórico no mesmo município"
reason_codes:
  - "top_1_percent_local"
  - "top_5_percent_local"
  - "amount_above_absolute_threshold"
  - "high_supplier_concentration_local"
---

# Detector: `large-local-contract-v1`

Regra determinística que cruza valor absoluto, percentil local histórico e concentração de fornecedor no município monitorado.
