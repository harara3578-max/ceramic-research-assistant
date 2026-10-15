# 仮説レコードJSON

`assets/example_hypotheses.json` が有効例。`scripts/validate_hypotheses.py` で必須キー・型・空欄・重複ID・観察との参照整合性を検査する。

最上位キー：
- `study_id`: 実験研究ID
- `observations`: 配列 `{id, statement, sample_ids, source}`。試料IDをつけられない場合は理由を記述する。
- `hypotheses`: 配列。各項目に `id`, `claim`, `mechanism`, `supporting_observation_ids` (配列), `contradicting_observation_ids` (配列、空可), `missing_evidence` (文字列), `alternative_explanations` (配列), `distinguishing_prediction` (文字列), `falsification_condition` (文字列), `proposed_test` (文字列), `limitations` (文字列) を含める。
- `overall_limitations`: 全体としての測定不足やバイアス。

検証ツールはJSONが充足しているか検査するのみ。仮説の真偽、出典の真実性、メカニズムの妥当性は判定しない。
