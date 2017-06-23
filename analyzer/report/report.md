# 2015年度長浜健康ウォークの解析

## 全体の狙い

現状の音声認識の枠組みを応用して、

1. 様々なヘルスレコードを統合的な特徴量に変換する手法を作れるか検討する
2. ユーザの内部状態（行動変容ステージ）推定をおこなえるかどうか検討する。
3. ヘルスケアエージェントの行動遷移モデルを（半）自動生成する枠組みを作れるかを検討する

うち、今回の解析では、1,2を行う。

## 音声認識の枠組み

![音声認識の仕組み](https://github.com/MxD-lab/healthrecord_analysis/wiki/images/asr.png)

## 提案予定のエージェントシステムの枠組み（ざっくり）

![エージェントシステムの枠組み](https://github.com/MxD-lab/healthrecord_analysis/wiki/images/agentsys.png)

## 今回の取り組み

### 様々なヘルスレコードを統合的な特徴量に変換する手法の検討

* 低次元化
	* 主成分分析（主に可視化のため）
	* Deep Sparse Autoencoder（こちらが本命）
* クラスタリング
	* Mean Shift クラスタリング
		* 確率密度の極大部を探索するMeanShift法を用いたクラスタリング。カーネル幅を指定することで、いくつのクラスタが存在するかを求めることができる
		* K-meanのようにkの値を指定しなくて良い

### ユーザの内部状態（行動変容ステージ）推定の検討

* ユーザ状態の推定
	* ユーザの状態推移をマルコフ連鎖と仮定
	* GMM-HMMにて推定
	* 特徴量をGMM近似して、そこからHMMの推定に持ち込む

## データの前処理

* 各個人のヘルスレコードを240次元のデータセットに変換
	* 1日を24時間に分割
	* 24時間 x 10日分のステップデータの配列を作成
	* Activityのstepsを時間分割
		* その時間に占めるstep数 / 全体のstep数

![Step数も時間分割](https://github.com/MxD-lab/healthrecord_analysis/wiki/images/step_sequence.png)

## チャレンジ全日程のパターン解析

### 作成したデータセット

![random choice](https://github.com/MxD-lab/healthrecord_analysis/wiki/images/datasets.random.png)

### 主成分分析

240次元のデータセットを主成分分析し、3次元プロットする。

![random choice](https://github.com/MxD-lab/healthrecord_analysis/wiki/images/240dim_pca.gif)

### データの前処理 Ver.2: Deep Sparse Autoencoderによる特徴量抽出

240次元から7層のDSAで30次元まで次元圧縮する

* Autoencoder:
	* 非教師学習による次元圧縮のためのニューラルネットワーク
* Sparse Autoencoder:
	* フィードフォワードニューラルネットワークの学習において汎化能力を高めるため、正則化項を追加したオートエンコーダのこと。ただし、ネットワークの重みではなく、中間層の値自体を0に近づける
	* より少ない(Sparseな)特徴量で入力を表現するように学習を行うため、クラスタリングのような効果を持つ
* Deep Autoencoder:
	* Autoencoderを多層化したもの

### DSA特徴量による主成分分析とMeanShiftクラスタリング

* MeanShiftクラスタリング(quantile=0.05)
* 8つのクラスタに分割

![dsa 30dim pca](https://github.com/MxD-lab/healthrecord_analysis/wiki/images/30dim_dsa_pca.gif)

## チャレンジ3日間ごとのパターン解析

### データの前処理

* 各個人のヘルスレコードを240次元のデータセットに変換
* 上記のデータを72時間を窓幅として24時間毎にスライド
* これにDSAを適用し、18次元に低次元化
	* データ数：5632
	* 次元数：18

### 主成分分析

3次元の主成分分析にかけ、プロット(3クラスタ)

![72 dim pca](https://github.com/MxD-lab/healthrecord_analysis/wiki/images/72dim_pca.gif)

### DSA特徴量によるクラスタリング

* MeanShiftクラスタリング(quantile=0.05)
* 13個のクラスタに分割

![dsa 18dim pca](https://github.com/MxD-lab/healthrecord_analysis/wiki/images/18dim_dsa_pca.gif)

## DNN-GMM-HMMへの適用

### DNN-GMM-HMMによる隠れ状態の推定

* 18次元のDSA特徴量、GMM-HMMにかける
* 状態の遷移を求める
* 得られた状態をクラスタリングし、ユーザの（内部）状態の推移パターンを調べる

![DSA-GMM-DNN](https://github.com/MxD-lab/healthrecord_analysis/wiki/images/DSA-GMM-HMM.png)

### 得られた状態列の主成分分析とMeanShiftクラスタリング

* 8状態、full connectionのHMMの場合
* 状態列をクラスタリングしたところ、21クラスに分類

![クラスタリング](https://github.com/MxD-lab/healthrecord_analysis/wiki/images/hmm_clustering.gif)

### なんか分かれているっぽいが・・実は

学習された遷移確率を可視化してみるとほとんど学習されていない（遷移確率の初期値は0.125 = 1.0 / 8.0だから）。初期値の確率が等分されているので、立方体の8つの頂点のどれかに値が集中しているだけ・・・

![状態遷移図](https://github.com/MxD-lab/healthrecord_analysis/wiki/images/state_transitions.png)

### 今後の取り組み

* 教師なし学習・クラスタリングで一般化された手法を組み合わせて、一通り解析を走らせてみた
* 手法の実装と解析スクリプトのサンプルを試作
* 現状得られているクラスタに意味があるかわからない（高い確率で意味がない）
* 意味があるクラスタ（とそれを分けるアルゴリズム）を発見し、それを元に解析を進めていく
* 一般化された手法からモデルや環境に応じた制約を加えていく（独自の手法やモデルの提案へ・・）

### 今後の取りくみ

1. 様々なヘルスレコードを統合的な特徴量に変換する手法を作れるか検討
	* データ統合
		* 距離の時系列情報の統合
		* Activity Typeの時系列情報の統合
		* チームの相互情報の統合
	* 入力データ設計
		* 朝・昼・夜など、メタ情報を考慮に入れた入力データの設計
	* 得られた特徴量・クラスタの検討
		* 歩数の増減や達成率などと比較することで、確かに有効な特徴量・クラスタであることを示す
2. ユーザの内部状態（行動変容モデル）推定をおこなえるかどうか検討
	* 適切な状態数の決定アルゴリズムの考察
	* 状態の意味するところの分析
3. ヘルスケアエージェントの行動遷移モデルを（半）自動生成する枠組みを作れるかを検討
	* ビヘイビアの定義と設計
	* エージェントの定義と設計
	* 日記帳の解析・・
