import streamlit as st
import streamlit.components.v1 as stc
import pandas as pd
import numpy as np
import glob
import pathlib
import os
import io
import plotly.io as pio
from io import StringIO, BytesIO
import base64
import pickle

#株価データを取得し、計算などをするために必要なもの
from yahoo_finance_api2 import share
from yahoo_finance_api2.exceptions import YahooFinanceError
import pandas as pd



#画像編集に必要なもの
from PIL import Image
from PIL import ImageFont
from PIL import ImageDraw


#日付などの取得
import time
import datetime


def cal_data_min(symbols,chart_type):

    #指定した銘柄の分足データ取得
    my_data = share.Share(str(symbols)+".T")
    symbol_data = None
    if chart_type == "1min":#7日間
        _dayRange = 7
        _min = 1
        symbol_data = my_data.get_historical(share.PERIOD_TYPE_DAY,_dayRange,share.FREQUENCY_TYPE_MINUTE,_min)
    if chart_type == "5min":
        _dayRange = 60
        _min = 5
        symbol_data = my_data.get_historical(share.PERIOD_TYPE_DAY,_dayRange,share.FREQUENCY_TYPE_MINUTE,_min)

    if chart_type == "15min":
        _minRange = 60
        _min = 15
        symbol_data = my_data.get_historical(share.PERIOD_TYPE_DAY,_minRange,share.FREQUENCY_TYPE_MINUTE,_min)

    if chart_type == "1hour":#730日間
        _monthRange = 24
        _min = 60
        symbol_data = my_data.get_historical(share.PERIOD_TYPE_MONTH,_monthRange,share.FREQUENCY_TYPE_MINUTE,_min)

    if chart_type == "1d":
        _yearRange = 25
        _day = 1
        symbol_data = my_data.get_historical(share.PERIOD_TYPE_YEAR,_yearRange,share.FREQUENCY_TYPE_DAY, _day)


    #加工できる形にデータ形式を変更
    df = pd.DataFrame(symbol_data)
    df["datetime"] = pd.to_datetime(df.timestamp, unit="ms")

    #timestampを日本時間へ変換
    df["datetime_jst"] = df["datetime"] + datetime.timedelta(hours=9)
    df["datetime"] = df["datetime"].astype(str)
    df["datetime_jst"] = df["datetime_jst"].astype(str)

    #データ取得できてるか確認用に末尾五行を表示
    #print(df.tail(5))


    ####データ加工をしていきます。今回は乖離率を出したいので分足の25MAとその乖離率を出します。
    #加工のために元データをコピーし、列名を変更し、データ抜けを削除した後、今回使うデータだけにしています
    df_copy = df.copy()
    df_copy.rename(columns={'datetime_jst': 'Date', 'open': 'Open',"high":"High","low":"Low",'close':'Close',"volume":"Volume"}, inplace=True)
    df_copy=df_copy.dropna()
    df2=df_copy.reindex(columns=["Date","Open","High","Low","Close","Volume"])

    #確認用
    #print(pdr.tail(5))


    #移動平均線と乖離率の計算　　　window=5　を変更すると期間を変えられます
    df2["sma25"] = df2["Close"].rolling(window=25).mean()
    #乖離率計算　２５MAで計算しています　（Moving average deviation rate　の頭文字で列名つけてます）
    df2["MAER"] = (df2["Close"] - df2["sma25"]) / df2["sma25"] * 100
    df2['Date'] = pd.to_datetime(df2['Date'])

    #乖離率の買い場・売り場の乖離率を計算し、表示
    m,s = df2["MAER"].mean(),df2["MAER"].std()
    deviation = (m-2*s)*-1/100
    lower = round((m-2*s),3)
    upper = round((m+2*s),3)

    df2["upper"] = df2["sma25"] + df2["sma25"] * deviation
    df2["lower"] = df2["sma25"] - df2["sma25"] * deviation

    return deviation , upper , lower, df2

@st.cache_data
def env_graph_show(df,chart_type,upper,lower):
    df2 = df.copy()
    import pandas as pd
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    # figを定義
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_width=[0.2,0.1, 0.6], x_title="Date")

    # Candlestick
    fig.add_trace(
        go.Candlestick(x=df2["Date"], open=df2["Open"], high=df2["High"], low=df2["Low"], close=df2["Close"], name="OHLC", showlegend=False),
        row=1, col=1)

    # Volume
    fig.add_trace(
        go.Bar(x=df2["Date"], y=df2["Volume"], name="Volume",marker_color='indianred', showlegend=False),
        row=2, col=1)

    # MAER
    fig.add_trace(
        go.Scatter(x=df2["Date"], y=df2["MAER"], name="KRI",marker_color = "orange", showlegend=False),
        row=3, col=1
    )

    fig.add_trace(
        go.Scatter(x=[df2["Date"].iloc[0],df2["Date"].iloc[-1]], y=[lower,lower],mode="lines", name="-KRI",line = dict(color='red', width=1.5), showlegend=False),
        row=3, col=1
    )

    fig.add_trace(
        go.Scatter(x=[df2["Date"].iloc[0],df2["Date"].iloc[-1]], y=[upper,upper],mode="lines", name="+KRI",line = dict(color='red', width=1.5), showlegend=False),
        row=3, col=1
    )

    # # Volume
    # fig.add_trace(
    #     go.Bar(x=df2["Date"], y=df2["Volume"], name="Volume", showlegend=False),
    #     row=3, col=1
    # )

    # SMA
    fig.add_trace(go.Scatter(x=df2["Date"], y=df2["sma25"], name="SMA25", mode="lines", line=dict(color="orange")), row=1, col=1)

    # Layout
    fig.update_layout(
        title={
            "text": chart_type +"チャート",
            "y":0.9,
            "x":0.5,
        }
    )

    # エンベロープ
    fig.add_trace(
        go.Scatter(x=df2["Date"], y=df2["upper"], name="エンベロープ", line=dict(width=1, color="blue")),
        row=1, col=1
    )
    fig.add_trace(
        go.Scatter(x=df2["Date"], y=df2["lower"], line=dict(width=1, color="blue"), showlegend=False),
        row=1, col=1
    )


    # y軸名を定義
    fig.update_yaxes(title_text="株価", row=1, col=1)
    fig.update_yaxes(title_text="出来高", row=2, col=1)

    if chart_type == "1d":
        gap_resample = df2.resample("1D", on='Date').max()
        timegap = gap_resample[gap_resample["Open"].isnull()].index.to_list()

        fig.update_layout(
            xaxis=dict(
                rangeselector=dict(
                    buttons=list([
                        dict(count=1,
                            label="1カ月",
                            step="month",
                            stepmode="backward"),
                        dict(count=6,
                            label="6カ月",
                            step="month",
                            stepmode="backward"),
                        dict(count=1,
                            label="年初来",
                            step="year",
                            stepmode="todate"),
                        dict(count=1,
                            label="1年",
                            step="year",
                            stepmode="backward"),
                        dict(step="all")
                    ])
                ),
                rangeslider=dict(
                    visible=False
                ),
                type="date"
            )
        )
        fig.update_xaxes(range = [df2["Date"].iloc[0],df2["Date"].iloc[-1]],rangebreaks=[dict(values= timegap)])

    else:#日足以外
        fig.update(layout_xaxis_rangeslider_visible=False)
        fig.update_xaxes(range = [df2["Date"].iloc[0],df2["Date"].iloc[-1]],rangebreaks=[
            dict(bounds=[15, 9], pattern="hour"),            # Remove non-trading hours
            dict(bounds=["sat", "mon"]),                        # Remove weekends
        ])

    #fig.show()
    return fig

@st.cache_data
def coding_process(_symbols,_N_list,_N_true):
    symbols = _symbols
    N_list = _N_list
    N_true = _N_true

    cols = {'標準偏差': [],  '理想乖離率：上限(%)': [], '理想乖離率：下限(%)': [],'ローソク足本数': []}
    df_dev = pd.DataFrame.from_dict(cols)# df
    dict_img = {}#各figデータを格納

    coding_data = code_header.replace("symbols",str(symbols))

    #プログレスバー
    progress_text = "処理中"
    my_bar = st.progress(0, text=progress_text)

    percent_complete = 0.0
    for n in range(len(N_list)):

        if N_list[n] == "1min":
            if N_true[n] == True:
                deviation ,upper  , lower, df__ = cal_data_min(symbols,"1min")
                # dev_1min = deviation
                # upper_1min = upper
                # lower_1min = lower
                # df_1min = df__.copy()
                # df_dev.loc["1分足"]=[dev_1min, upper_1min, lower_1min,int(len(df_1min))]
                # fig_1min = env_graph_show(df_1min)

                df_dev.loc["1分足"]=[deviation, upper, lower,int(len(df__))]
                dict_img.update({N_list[n]:env_graph_show(df__,N_list[n],upper,lower)})
                coding_data = coding_data + code_1min.replace("upper_1min_data",str(upper)).replace("lower_1min_data",str(lower))
            else:
                pass

        if N_list[n] == "5min":
            if N_true[n] == True:
                deviation ,upper  , lower, df__ = cal_data_min(symbols,"5min")
                # dev_5min = deviation
                # upper_5min = upper
                # lower_5min = lower
                # df_5min = df__.copy()
                # df_dev.loc["5分足"]=[dev_5min, upper_5min, lower_5min,int(len(df_5min))]
                # fig_5min = env_graph_show(df_5min)

                df_dev.loc["5分足"]=[deviation, upper, lower,int(len(df__))]
                dict_img.update({N_list[n]:env_graph_show(df__,N_list[n],upper,lower)})

                coding_data = coding_data + code_5min.replace("upper_5min_data",str(upper)).replace("lower_5min_data",str(lower))
            else:
                pass


        if N_list[n] == "15min":
            if N_true[n] == True:
                deviation ,upper  , lower, df__ = cal_data_min(symbols,"15min")
                # dev_15min = deviation
                # upper_15min = upper
                # lower_15min = lower
                # df_15min = df__.copy()
                # df_dev.loc["15分足"]=[dev_15min, upper_15min, lower_15min,int(len(df_15min))]
                # fig_15min = env_graph_show(df_15min)

                df_dev.loc["15分足"]=[deviation, upper, lower,int(len(df__))]
                dict_img.update({N_list[n]:env_graph_show(df__,N_list[n],upper,lower)})

                coding_data = coding_data + code_15min.replace("upper_15min_data",str(upper)).replace("lower_15min_data",str(lower))
            else:
                pass

        if N_list[n] == "1hour":
            if N_true[n] == True:
                deviation ,upper  , lower, df__ = cal_data_min(symbols,"1hour")
                # dev_1hour = deviation
                # upper_1hour = upper
                # lower_1hour = lower
                # df_1hour = df__.copy()
                # fig_1hour = env_graph_show(df__,N_list[n],upper,lower)

                df_dev.loc["1時間足"]=[deviation, upper, lower,int(len(df__))]
                dict_img.update({N_list[n]:env_graph_show(df__,N_list[n],upper,lower)})

                coding_data = coding_data + code_1hour.replace("upper_1hour_data",str(upper)).replace("lower_1hour_data",str(lower))
            else:
                pass

        if N_list[n] == "1d":
            if N_true[n] == True:
                deviation ,upper  , lower, df__ = cal_data_min(symbols,"1d")
                # dev_1d = deviation
                # upper_1d = upper
                # lower_1d = lower
                # df_1d = df__.copy()
                # fig_1d = env_graph_show(df__,N_list[n],upper,lower)

                df_dev.loc["日足"]=[deviation, upper, lower,int(len(df__))]
                dict_img.update({N_list[n]:env_graph_show(df__,N_list[n],upper,lower)})
                coding_data = coding_data + code_1day.replace("upper_1day_data",str(upper)).replace("lower_1day_data",str(lower))

            else:
                pass

        percent_complete += 1/len(N_list)
        if percent_complete <= 1:
            my_bar.progress(percent_complete, text=progress_text)

    # df_dev_ = df_dev.style.format(precision=3).format(subset='ローソク足本数',precision=0).format(subset='標準偏差',precision=5)
    coding_data = coding_data + code_Alert
    my_bar.empty()

    return dict_img, df_dev, coding_data

#plotlyの白黒を直す。
pio.templates.default = "plotly"


#github
st.set_page_config(layout="wide")

#code材料
f = open("files/code_header.txt", 'r')
code_header = f.read()

f = open("files/code_1min.txt", 'r')
code_1min = f.read()

f = open("files/code_5min.txt", 'r')
code_5min = f.read()

f = open("files/code_15min.txt", 'r')
code_15min = f.read()

f = open("files/code_1hour.txt", 'r')
code_1hour = f.read()

f = open("files/code_1day.txt", 'r')
code_1day = f.read()

f = open("files/code_Alert.txt", 'r')
code_Alert = f.read()


stc.html(
'''
<style type="text/css">
<!--
#QandA-1 {
	width: 100%;
	font-family: メイリオ;
	font-size: 14px; /*全体のフォントサイズ*/
}
#QandA-1 h2 {

}
#QandA-1 dt {
	background: #444; /* 「Q」タイトルの背景色 */
	color: #fff; /* 「Q」タイトルの文字色 */
	padding: 8px;
	border-radius: 2px;
}
#QandA-1 dt:before {
	content: "・";
	font-weight: bold;
	margin-right: 8px;
}
#QandA-1 dd {
	margin: 24px 16px 40px 32px;
	line-height: 140%;
	text-indent: -24px;
}
#QandA-1 dd:before {
	content: "・";
	font-weight: bold;
	margin-right: 8px;
}

-->
</style>

<div id="QandA-1">
	<h2>Trading Viewの理想乖離エンベロープのインジケータ生成アプリ</h2>
	<h3>アプリの背景</h3>
	<dl>
		<dt>エンベロープとは？</dt>
		<dd>エンベロープは、移動平均線から上下に一定に乖離させた線のことで、移動平均線からどれくらい乖離しているのかを一目で確認することができます。<br>
            移動平均線から乖離しすぎた株価は最終的には移動平均線に収束するという特性があるので、この特性を利用して反転のポイントを見つけたり、支持線や抵抗線として利用することもできます。</dd>
		<dt>理想な乖離率とは？</dt>
		<dd>一方、銘柄により効果的な乖離率は異なります。<br>
            通常は目視によって乖離率を把握しますが、ここでは標準偏差(σ)を用い、統計的に反発が期待できる乖離率を計算します。<br>
            また乖離率の中央値は必ずしも0にはならないため、上限値/下限値は別々に算出されます。</dd>
		<dt>質問タイトル</dt>
		<dd>回答内容<br>回答内容</dd>
	</dl>

	<h3>本アプリの機能</h3>
	<dl>
		<dt>①Trading Viewのエンベロープインジケータを自動生成</dt>
		<dd>ダウンロード可能<br>アラート設定も可能</dd>
		<dt>②理想乖離率の保存</dt>
		<dd>詳細<br>詳細</dd>
		<dt>③計算利用本数(==信頼度)をチェック</dt>
		<dd>詳細<br>詳細</dd>
		<dt>④チャートイメージを生成</dt>
		<dd>Trading Viewを利用しない場合もアプリ内でチャートを確認し反発などをチェックできます。<br>詳細</dd>

	</dl>
</div>
''',
height=1200,#設定しないと埋まる
)


# st.title("Trading Viewの理想乖離エンベロープのインジケータ生成アプリ")

# text = '''
# Trading Viewで各時間足の移動平均乖離率を用いたエンベロープのインジケータを生成しよう。

# エンベロープは、移動平均線から上下に一定に乖離させた線のことで、移動平均線からどれくらい乖離しているのかを一目で確認することができます。
# 移動平均線から乖離しすぎた株価は最終的には移動平均線に収束するという特性があるので、この特性を利用して反転のポイントを見つけたり、支持線や抵抗線として利用することもできます。

# 一方、銘柄により効果的な乖離率は異なります。
# 通常は目視によって乖離率を設定しますが、ここでは統計的に反発が期待できる乖離率を計算します。
# ※標準偏差（σ）を用いた2σ(約95.5%以上の乖離)

# 銘柄毎に効果的な乖離率の算出＋インジケータの調整は大変ですが、
# こちらのアプリで生成したコードをTrading Viewに貼付ければOK。

# '''


# st.write(text)
# st.write("まだTrading Viewの無料アカウントを作っていない方は[こちらからどうぞ！](https://jp.tradingview.com/?aff_id=127468)")


# Github
# https://www.jpx.co.jp/markets/statistics-equities/misc/01.html
url = 'https://www.jpx.co.jp/markets/statistics-equities/misc/tvdivq0000001vg2-att/data_j.xls'
df_jpx = pd.read_excel(url)
df_jpx = df_jpx.iloc[:, [1, 2, 3, 9]]
database = df_jpx[df_jpx["市場・商品区分"] != "ETF・ETN"]
database = database.astype(str)

# # Local
# url = "/content/drive/MyDrive/master_ColabNotebooks/kabu_files/test_account_files/230719 Env/data_j_202311.xls"
# df_jpx = pd.read_excel(url)
# df_jpx = df_jpx.iloc[:, [1, 2, 3, 9]]
# database = df_jpx[df_jpx["市場・商品区分"] != "ETF・ETN"]
# database = database.astype(str)


# 指定した銘柄コードと期間でデータを取得をします。
# symbols → 個別株・指数のコード

with st.form(key='form1'):
    st.cache_data.clear()

    input_txt = st.text_input('銘柄コードを入力 or 部分一致の検索', '8058')

    DB_result = database[(database['コード'].str.contains(str(input_txt)))|(database['銘柄名'].str.contains(str(input_txt)))]
    st.table(DB_result)
    if len(DB_result) == 0:
        st.write("一致する銘柄はありません")
    if len(DB_result) > 1:
        st.write("1銘柄になるように入力してください")
    if len(DB_result) == 1:
        symbols = DB_result.iloc[0,0]
        name = DB_result.iloc[0,1]
        st.write(f"[・TradingViewで開く](https://jp.tradingview.com/chart/?symbol=TSE%3A{symbols})")
        st.write(f"[・株探で確認する](https://kabutan.jp/stock/chart?code={symbols})")

    st.write("データの必要な時間足：")
    _1min = st.checkbox('1min')
    _5min = st.checkbox('5min')
    _15min = st.checkbox('15min')
    _1hour = st.checkbox('1hour',value=True)
    _1d = st.checkbox('1day',value=True)

    chart_radio = st.radio(label="チャートの表示",options = ("アプリ内で表示","Trading Viewで確認する。"),index=0,horizontal=True)
    if chart_radio == "アプリ内で表示":
        st.warning("選択している時間足が多いとチャート表示に時間が掛かることがあります。")

    st.warning("銘柄を変更した場合、実行ボタンを押さないとデータが反映されません。")
    submit = st.form_submit_button("実行")

if submit:
    st.session_state.submitted = True
    N_list = ["1min","5min","15min","1hour","1d"]
    N_true = [_1min, _5min, _15min, _1hour, _1d]

    dict_img,df_dev,coding_data = coding_process(symbols,N_list,N_true)

if 'submitted' in st.session_state:
    N_list = ["1min","5min","15min","1hour","1d"]
    N_true = [_1min, _5min, _15min, _1hour, _1d]

    #if st.session_state.value == 0:
    #st.write("if st.session_state.value == 0,start")
    #dict_img,df_dev,coding_data = coding_process(symbols,N_list,N_true)
    #st.session_state.value = 1

    #st.write(st.session_state.value)

    #if st.session_state.value == 1:

    dict_img,df_dev,coding_data = coding_process(symbols,N_list,N_true)

    #プログレスバー
    if chart_radio == "アプリ内で表示":
        progress_text = "処理中"
        my_bar = st.progress(0, text=progress_text)
        percent_complete = 0.0
        with st.expander("チャートの表示📈", expanded=False):
            st.write("拡大縮小など任意の位置で保存可能です：📷")
            for mykey, myvalue in dict_img.items():

                st.write("時間足：",mykey)
                st.plotly_chart(myvalue, use_container_width=True)

                percent_complete += 1/len(N_list)
                if percent_complete <= 1:
                    my_bar.progress(percent_complete, text=progress_text)
            my_bar.empty()

    df_dev_ = df_dev.style.format(precision=3).format(subset='ローソク足本数',precision=0).format(subset='標準偏差',precision=5)
    st.write(df_dev_)
    df_filename =  "EnvCode_" +symbols + "_" + name + ".csv"
    csv_ = df_dev.to_csv().encode('cp932')
    st.download_button(label="表をダウンロード", data = csv_, file_name = df_filename,mime='text/csv')

    st.write("Pineコード:" + symbols + " " + name)
    code_filename =  "EnvCode_" +symbols + "_" + name + ".txt"
    st.download_button(label="コードをダウンロード",file_name = code_filename, data = coding_data,mime="text/plain")
    st.code(coding_data)
