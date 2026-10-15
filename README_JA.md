# 電子セラミック材料開発 統合Skill v1.0.0

**1つのSkillの中に**、データ品質確認、記述統計、競合仮説生成、批判的レビュー、一次XRDピーク検出、次回実験計画をまとめた社内向けZIPです。既存の別Skillの自動ロードや外部APIに依存しません。

## 導入方法
1. 会社のソフトウェア／コード持ち込み審査を受け、このZIPを社内へ持ち込んでください。
2. ZIPを展開し、`ceramic-research-assistant` フォルダを社内AIのSkillsディレクトリに配置するか、Skillインポート機能で指定してください。取り込み方法は製品依存です。
3. 社内AIに「ceramic-research-assistant を使用して、これらの測定データを考察してください」と依頼してください。
4. 社内AIがファイル読込やPython実行に対応している場合のみ、付属CLIを実行できます。チャット専用AIでは指示文と参照資料のみ利用できます。

## 事前条件
- Agent Skillsを読み込める社内AI（またはシステム指示としてSKILL.mdを登録できる環境）
- CLI実行する場合のみ **Python 3.10以降**（標準ライブラリだけ）
- Python環境の持ち込みも社内ルールに従う
- OS側でも外向き通信を遮断する。Skillの宣言だけでは、社内AIプラットフォームのネットワーク挙動を制御できません。

## 最初の動作確認
Skillフォルダに移動して以下を実行します。

```powershell
python -m unittest discover -s tests -v
python scripts/analyze_experiments.py --input assets/example_experiments.csv --out-dir output/eda
python scripts/xrd_peak_screen.py --input assets/example_xrd.csv --output output/xrd_peaks.csv
python scripts/validate_hypotheses.py --input assets/example_hypotheses.json
python scripts/plan_experiments.py --input assets/example_design.json --output output/design.csv
```

結果ファイルは `output/` に作成されます。原本は読み取りのみ。サンプルデータは全て**架空**です。

## ディレクトリ案内
- `SKILL.md` — 社内AIに読ませる本体
- `references/` — 電子セラミック専門知識、データ列仕様、仮説の構造、レポート様式、安全・出典
- `scripts/` — 完全ローカルのPython CLI
- `assets/` — サンプルCSV/JSON（架空）
- `tests/` — 動作確認テスト

## 範囲と注意
既存K-Dense Skillの**研究手順を参考に新規に再構成した統合Skill**です。各リポジトリの元スクリプトを同梱していません。K-Dense製品との公式な互換性認証もありません。XRDのピーク検出は探索用で、相同定・格子定数精密化・リートベルト解析を実装していません。実験計画ジェネレータは小規模な全因子・反復・順序のランダム化のみ。仮説の質は社内AIと研究者のレビューに依存します。

## 社内で確認すること
1. Skillの取り込み形式、Python実行可否、利用可能なファイル権限
2. ZIP内コードの静的監査、持ち込み承認、ネットワーク遮断
3. 秘密情報の保存先、生成ファイルの管理、保管期限
4. 社内AIの外部接続設定とログ・学習利用条件

MITライセンスおよび参照元を `LICENSE` と `references/PROVENANCE.md` に記載。
