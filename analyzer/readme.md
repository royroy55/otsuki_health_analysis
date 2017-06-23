# healthrecord_analysis

tekupekoのデータ解析をするプロジェクトです。

# OSXにおけるセットアップ

## 必要なソフトウェアのインストール（オプショナル）

gifの編集ソフトウェアをインストールします。

```
$ brew install gifsicle
```

## パッケージのインストール

以下のコマンドで必要パッケージをインストールしてください。

```
$ brew install pyenv imagemagick
$ pyenv install anaconda-2.4.0
```

.bashrc に以下を追加

``` .bashrc
PYENV_ROOT="${HOME}/.pyenv"
if [ -d "${PYENV_ROOT}" ]; then
    export PATH=${PYENV_ROOT}/bin:$PATH
    eval "$(pyenv init -)"
fi
```

以下 bash での作業

``` bash
% source ~/.bashrc
% pyenv global anaconda-2.4.0
% conda install scikit-learn
$ pip install django chainer hmmlearn
```

## プロジェクトのclone

下記、コマンドを利用して、プロジェクトをcloneします。

```
$ git clone https://github.com/MxD-lab/healthrecord_analysis.git
$ cd healthrecord_analysis
```

## 使い方

実装されているコマンドはmanage.pyのヘルプで確認することができます。

```
$ cd analyzer
$ manage.py --help

Type 'manage.py help <subcommand>' for help on a specific subcommand.

Available subcommands:

[auth]
    changepassword
    createsuperuser
...
[record]
    create_datasets
    draw_graph
    exec_dsa
    exec_pca
    loadmoves
```

[record]と書かれている部分が実装したコマンドです。コマンドの詳細は各サブコマンドのヘルプを参照してください。

```
$ manage.py create_datasets --help
usage: manage.py create_datasets [-h] [--version] [-v {0,1,2,3}]
                                 [--settings SETTINGS]
                                 [--pythonpath PYTHONPATH] [--traceback]
                                 [--no-color]

create datasets from db
```

### データセットの概念

プロジェクトで生成されるデータセットやクラスタリングの結果はnpzという拡張子で保存されます。大抵の場合は、

* datasets.npz

というファイルに保存されることになります。これはnumpyのデータ形式の一つでキーワードとして文字列、値として
numpyのデータ型が入っています。下記に簡単に書き込みと読み込みのコードを紹介します。

#### データセットへの書き込み

データセットの保存時のコードです。npzファイルへの書き込みは、numpy.savez\_compressedという関数を使って行われます。
関数の第一引数はファイルオブジェクト、第二引数以降に、データのkeyとvalueを登録します。

```
import numpy

datasets_x = <numpy structure>
datasets_y = <numpy structure>

with open('datasets.npz', 'wb') as fp:
  numpy.savez_compressed(fp, x=datasets_x, y=datasets_y)
```

#### データセットの読み込み

npzファイルの読み込みは以下のコードで行うことができます。注意点としては、ファイルのデータへのアクセスは、
実際に辞書型へのキーのアクセスがあった時に行われます。したがって、辞書型の値の読み込みが済むまでは
ファイルオブジェクトは開いた状態でなければなりません。

```
import numpy

with open('datasets.npz', 'rb') as fp:
  datasets = numpy.load(fp)
  x = datasets['x']
  y = datasets['y']
```

以下はNGなコードです。

```
import numpy

with open('datasets.npz', 'rb') as fp:
  datasets = numpy.load(fp)

x = datasets['x']
y = datasets['y']
```


解析スクリプトは、npzファイルからデータセットを読み込み、解析した内容を新しいAttributeとして追記していきます。
したがって、見た目上は、datasets.npzというファイルのみがあり、そのサイズが増えていくことになります。

解析を進めるにあたって、このデータファイルの特性を知っておきましょう。

### create_datasets

サブコマンドcreate_datasetsは、analyze.dbからデータを読みだし、240次元のデータセットを作成します。

### exec_pca

サブコマンドexec_pcaは、与えられたデータセットの主要因分析を行い、得られた 3 次元のデータをプロットします。
オプション--enable\_animationにより、アニメーションgifの作成や、--enable\_clusteringでMeanShiftクラスタリングも行います。

```
$ manage.py exec_pca --help

usage: manage.py exec_pca [-h] [--version] [-v {0,1,2,3}]
                          [--settings SETTINGS] [--pythonpath PYTHONPATH]
                          [--traceback] [--no-color] [--dataid DATAID]
                          [--enable_animation] [--gif GIF]
                          [--azimuth_interval AZIMUTH_INTERVAL]
                          [--elevation ELEVATION] [--fps FPS]
                          [--enable_clustering] [--quantile QUANTILE]
                          target

create sample userdata graph

positional arguments:
  target                target pickle file.

optional arguments:
  -h, --help            show this help message and exit
  --version             show program's version number and exit
  -v {0,1,2,3}, --verbosity {0,1,2,3}
                        Verbosity level; 0=minimal output, 1=normal output,
                        2=verbose output, 3=very verbose output
  --settings SETTINGS   The Python path to a settings module, e.g.
                        "myproject.settings.main". If this isn't provided, the
                        DJANGO_SETTINGS_MODULE environment variable will be
                        used.
  --pythonpath PYTHONPATH
                        A directory to add to the Python path, e.g.
                        "/home/djangoprojects/myproject".
  --traceback           Raise on CommandError exceptions
  --no-color            Don't colorize the command output.
  --dataid DATAID       dataid for npz file
  --enable_animation    whether to activate and save animation gif. [default:
                        False]
  --gif GIF             file path to save animation gif. [default: "pca.gif"]
  --azimuth_interval AZIMUTH_INTERVAL
                        interval of azimuth. [default: 5.]
  --elevation ELEVATION
                        elevation of camera. [default: 10.]
  --fps FPS             fps of gif animation. [default: 4]
  --enable_clustering   whether to enable mean shift clustering. [default:
                        False]
  --quantile QUANTILE   quantile for mean shift clustering. [default: 0.05]

```

実行例は以下のとおりです。

```
$ manage.py exec_pca --enable_animation --enable_clustering --dataid all datasets.npz
```

### exec_dsa

サブコマンドexec_dsaは、7階層のDeep Sparse Autoencoderを実行し、学習されたネットワークで生成した特徴量をtargetに追加します。
オプションとして、--hiddensで隠れ層の次元数を、--epochsで学習回数を指定できます。


```
$ manage.py exec_dsa --help
usage: manage.py exec_dsa [-h] [--version] [-v {0,1,2,3}]
                          [--settings SETTINGS] [--pythonpath PYTHONPATH]
                          [--traceback] [--no-color] [--dataid DATAID]
                          [--hiddens HIDDENS [HIDDENS ...]] [--epochs EPOCHS]
                          target

create sample userdata graph

positional arguments:
  target                target pickle file.

optional arguments:
  -h, --help            show this help message and exit
  --version             show program's version number and exit
  -v {0,1,2,3}, --verbosity {0,1,2,3}
                        Verbosity level; 0=minimal output, 1=normal output,
                        2=verbose output, 3=very verbose output
  --settings SETTINGS   The Python path to a settings module, e.g.
                        "myproject.settings.main". If this isn't provided, the
                        DJANGO_SETTINGS_MODULE environment variable will be
                        used.
  --pythonpath PYTHONPATH
                        A directory to add to the Python path, e.g.
                        "/home/djangoprojects/myproject".
  --traceback           Raise on CommandError exceptions
  --no-color            Don't colorize the command output.
  --dataid DATAID       id for npz file. [default: None]
  --hiddens HIDDENS [HIDDENS ...]
                        dimentions of hidden layers. [default: []]
  --epochs EPOCHS       epochs for SdA. [default: 100]
```

実行例は以下のとおりです。

```
$ manage.py exec_dsa --epochs 1000 --hiddens 72 36 18 --dataid 3 datasets.npz
```

### exec_hmm

サブコマンドexec_hmmは、DSA特徴量の時系列情報を観測列とし、GMM-HMMによる隠れ状態の学習を行います。
そして、学習された遷移確率・出力確率をベースに、各特徴量の時系列データから推定される内部状態列を推定し、
その内容をtargetに追記します。

```
$ manage.py exec_hmm --help
usage: manage.py exec_hmm [-h] [--version] [-v {0,1,2,3}]
                          [--settings SETTINGS] [--pythonpath PYTHONPATH]
                          [--traceback] [--no-color] [--dataid DATAID]
                          [-c COMPONENTS] [-m MIX] [--enable_state_graph]
                          target

create sample userdata graph

positional arguments:
  target                target npz file.

optional arguments:
  -h, --help            show this help message and exit
  --version             show program's version number and exit
  -v {0,1,2,3}, --verbosity {0,1,2,3}
                        Verbosity level; 0=minimal output, 1=normal output,
                        2=verbose output, 3=very verbose output
  --settings SETTINGS   The Python path to a settings module, e.g.
                        "myproject.settings.main". If this isn't provided, the
                        DJANGO_SETTINGS_MODULE environment variable will be
                        used.
  --pythonpath PYTHONPATH
                        A directory to add to the Python path, e.g.
                        "/home/djangoprojects/myproject".
  --traceback           Raise on CommandError exceptions
  --no-color            Don't colorize the command output.
  --dataid DATAID       id for npz file. [default: None]
  -c COMPONENTS, --components COMPONENTS
                        number of components in GMM-HMM. [default: 4]
  -m MIX, --mix MIX     number of gaussian mixture in GMM-HMM. [default: 8]
  --enable_state_graph  Whether to create sampled state graph for each class.
                        [default: False]
```

実行例は以下のとおりです。

```
$ manage.py exec_hmm --dataid dsa datasets.npz
```