# hass_looop_price_tracker

[Looop でんき](https://looop-denki.com/)の電力料金情報をHome Assistantで監視できる統合です。

## 概要

この統合により、Looop でんきの「でんき予報」データをリアルタイムで取得し、Home Assistantのセンサーとして表示できます。電力料金の変動を監視して、電気代の節約や自動化に活用できます。

## 機能

- **リアルタイム電力料金監視**: 30分単位で更新される現在の電力料金
- **価格ステータス表示**: でんき日和、でんき注意報、でんき警報の判定

<!--
## インストール

### HACS経由（推奨）
1. HACSを開く
2. 「統合」→「カスタムリポジトリ」
3. リポジトリURL を追加
4. 「Looop でんき」を検索してインストール
5. Home Assistantを再起動

### 手動インストール
1. `custom_components/looop_denki/` フォルダを作成
2. 統合ファイルをフォルダにコピー
3. Home Assistantを再起動
-->

## 設定

1. **統合の追加**
   - 設定 → デバイスとサービス → 統合を追加
   - 「Looop でんき」を検索
   - または直接URL: `/config/integrations/add?domain=looop_denki`

2. **電力エリア選択**
   - お住まいの電力エリアを選択してください
   - 東京電力エリアの場合は「03 - 東京電力」を選択

3. **完了**
   - 統合が正常に設定されると、センサーが作成されます

## センサー情報

### メインセンサー: `sensor.looop_denki_current_price_*`

- **値**: 現在の電力料金（円/kWh）
- **単位**: 円/kWh
- **更新間隔**: 5分

### 属性

| 属性名 | 説明 | 例 |
|--------|------|-----|
| `current_level` | 価格レベル（-0.5〜0.5） | -0.5 |
| `current_text` | 詳細情報 | "Price: 12.3, Level: -0.5" |
| `status` | 価格ステータス | "でんき日和" |
| `time_slot` | 30分単位のタイムスロット | 24 |
| `hour` | 現在の時間 | 12 |
| `minute_range` | 分の範囲 | "00-29" |

### 価格ステータス

- **でんき日和** 🌞: 電力料金が安い時間帯（電気使用推奨）
- **でんき注意報** ⚠️: 電力料金が高い時間帯（使用を控えめに）
- **でんき警報** 🚨: 電力料金が非常に高い時間帯（100円/kWh以上）

## 自動化の例

### 安い時間帯に洗濯機を動かす

```yaml
automation:
  - alias: "安い電気で洗濯"
    trigger:
      - platform: state
        entity_id: sensor.looop_denki_current_price_tokyo
        attribute: status
        to: "でんき日和"
    condition:
      - condition: time
        after: "22:00:00"
        before: "06:00:00"
    action:
      - service: switch.turn_on
        entity_id: switch.washing_machine
```

### 高い時間帯に通知

```yaml
automation:
  - alias: "電気代高騰通知"
    trigger:
      - platform: state
        entity_id: sensor.looop_denki_current_price_tokyo
        attribute: status
        to: "でんき警報"
    action:
      - service: notify.mobile_app
        data:
          message: "⚠️ 電力料金が高騰しています！電気の使用を控えましょう"
```

## トラブルシューティング

### センサーが利用不可能

1. **ネットワーク接続確認**
   - Home Assistantからインターネットにアクセスできるか確認

2. **ログ確認**
   ```yaml
   logger:
     default: info
     logs:
       custom_components.looop_denki: debug
   ```

3. **統合の再読み込み**
   - 設定 → デバイスとサービス → Looop でんき → 再読み込み

## ライセンス

MIT License

## 免責事項

- この統合は非公式のサードパーティ製品です
- Looop でんき社とは無関係です
- データの正確性は保証されません
- 重要な判断は公式サイトでご確認ください

---

💡 **ヒント**: Home Assistantのエネルギーダッシュボードと組み合わせて、電力消費と料金の両方を監視しましょう！
