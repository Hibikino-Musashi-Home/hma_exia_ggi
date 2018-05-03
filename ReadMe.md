# Go Get It in Unknown Environment
本リポジトリは，Hibikino-Musashi@Home（本チーム）が
RoboCup Japan Open 2018 で
Go Get It in Unknown Environmentを達成する際に用いたプログラムである．

本リポジトリは，以下のソースコードを含む．
* sm\_ggi.py：タスク設計プログラム
* double\_metaphone\_server.py：DoubleMetaphoneアルゴリズムにより音の近さを計算するサービスサーバ

## 実行環境
* Ubuntu14.04
* ROS Indigo

## 達成手法
### 概要
本タスクでは，音声情報から地点・物体の学習を行う.
本タスクは学習時間が短いため,目標性能の確保にビックデータが必要な関数ベースの機械学習を避け,
プロトタイプとの距離比較で認識を行うことで,データベース構築に必要な学習時間を短縮する．
Training Phase では音声情報から場所と物体をデータベース化し，
Test Phase では，音声命令から取得した単語とデータベースに格納された単語間の距離を算出することで，
尤もらしい場所へ移動し命令を実行する．

### Training Phase
本タスクにおけるTraining Phaseでは，下記のAPIやアルゴリズム，ライブラリを用いる．
* Web Speech API （Google Chrome）：英語音声認識
* Python Metaphoneライブラリ（Double Metaphone アルゴリズム）：英単語の発音記号化

また，本フェーズは下記の手順で実行され，学習が行われる．
1. 話者は,場所と物体の特徴を単語レベルでロボットへと教示する．
2. 教示により入力された英語音声をGoogle Chrome の Web Speech APIを利用し文字起こしする．
3. 文字起こしされた文を，Double Metaphone アルゴリズムを用いて音声発音を表すコード(発音記号)に変換する．
4. この時,物体の場所情報(TV などの場所の名前と座標)と特徴情報(Red object など)をそれぞれ別のデータベースに保存する．
5. 以上のステップを,物体および場所の特徴を判別できる程度に繰りかえして Training Phase を終了する．

### Test Phase
本タスクにおけるTraining Phaseでは，下記のAPIやアルゴリズムを用いる．
* Web Speech API （Google Chrome）：英語音声認識
* Python NLTKライブラリ：形態素解析
* Python Metaphoneライブラリ（Double Metaphone アルゴリズム）：英単語の発音記号化
* Python Levenshteinライブラリ：英単語のレーベンシュタイン距離測定

また，本フェーズは下記の手順で実行される．
1. 話者は「Breng me ＊」の命令コマンドを音声でロボットへ与える．
2. 入力された英語音声をGoogle Chrome の Web Speech APIを利用し文字起こしする．
3. 形態素解析を用いた品詞分けにより,名詞(NN)と形容詞(JJ)を抽出する．
4. 品詞分けされて抽出された単語を,学習時と同様に,発音記号に変換する．
5. 学習時の発音記号とのレーベンシュタイン距離を算出し,あらかじめ定めておいた閾値以下になった場合,命令文にキーワードが含まれているとカウントする．
6. 最もキーワードが一致した地点を候補とし,場所の情報を格納したデータベースより必要な情報(場所の名前と座標)を参照すると共に,オペレータに移動許可を求める．

## 詳細
本手順は，下記PDFファイルにより詳細にまとめた．
[https://github.com/hibikino-musashi-athome/hma_exia_ggi/raw/master/Hibikino_ggi.pdf](https://github.com/hibikino-musashi-athome/hma_exia_ggi/raw/master/Hibikino_ggi.pdf)
