import os
import sys
from ui_layout import Ui_MainWindow
from qtpy.QtWidgets import QApplication, QMainWindow, QFileDialog, QMessageBox
from PyQt5.QtCore import QUrl, pyqtSignal, QObject, QDateTime, QDate, QTime
import Ipynb_importer
import iwencai
import pickle
import pandas as pd
from threading import Thread
import plotly
import plotly.graph_objs as go
import datetime

RENDER_FILE = iwencai.ROOT_DIR + '/render.html'


class emittingStream(QObject):
    textWritten = pyqtSignal(str)  # 定义一个发送str的信号

    def write(self, text):
        self.textWritten.emit(str(text))

    def flush(self):
        pass


class MyUi(QMainWindow):
    def __init__(self):
        super(MyUi, self).__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        # 重定向标准输出stdout
        sys.stdout = emittingStream(textWritten=self.outputWritten)
        # 改变窗体大小并居中
        rect = QApplication.desktop().screenGeometry()
        self.resize(rect.width() - 100, rect.height() - 200)
        size = self.geometry()
        self.move(
            (rect.width() - size.width()) / 2,
            (rect.height() - size.height()) / 2)
        # 初始化控件
        self.ui.marketComboBox.addItems(mk['name'] for mk in iwencai.MARKET)
        self.ui.marketMethodComboBox.addItems(mt['name'] for mt in iwencai.METHOD)
        self.ui.classifiedMethodComboBox.addItems(mt['name'] for mt in iwencai.METHOD)

        self.ui.marketSeriesComboBox.addItems(
            st for st in iwencai.STATISTIC_COLUMN)
        self.ui.classifiedSeriesComboBox.addItems(
            st for st in iwencai.STATISTIC_COLUMN)
        self.ui.stockSeriesComboBox.addItems(
            st for st in iwencai.STATISTIC_COLUMN)
        self.ui.classifiedComboBox.addItems(
            cl for cl in iwencai.CLASSICFICATION)

        self.ui.basicDataLineEdit.setText(iwencai.BASIC_DATA_DIR)
        self.ui.stockDataLineEdit.setText(iwencai.STOCK_DATA_DIR)
        self.ui.allStockLineEdit.setText(iwencai.ALL_STOCK_FILE)
        self.ui.statisticLineEdit.setText(iwencai.STATISTIC_FILE)
        self.ui.classifiedLineEdit.setText(iwencai.CLASSIFIED_FILE)

        self.ui.startDateEdit.setDateTime(
            QDateTime(
                QDate(
                    2001, 1, 1), QTime(
                    0, 0, 0)))
        self.ui.endDateEdit.setDateTime(
            QDateTime(
                QDate(
                    datetime.datetime.now().year, 12, 31), QTime(
                    0, 0, 0)))

        # 设置signal/slot
        self.ui.addMarketSeriesButton.clicked.connect(
            lambda: self.addSeries('M', self.ui.marketComboBox.currentText(),
                                   self.ui.marketMethodComboBox.currentText(),
                                   self.ui.marketSeriesComboBox.currentText()))
        self.ui.addClassifiedSeriesButton.clicked.connect(
            lambda: self.addSeries(
                'C',
                self.ui.classifiedComboBox.currentText(),
                self.ui.classifiedMethodComboBox.currentText(),
                self.ui.classifiedSeriesComboBox.currentText()))
        self.ui.addStockSeriesButton.clicked.connect(
            lambda: self.addSeries('S', self.ui.stockLineEdit.text(), '值',
                                   self.ui.stockSeriesComboBox.currentText()))

        self.ui.saveButton.clicked.connect(lambda: self.saveSeries())
        self.ui.loadButton.clicked.connect(lambda: self.loadSeries())
        self.ui.deleteButton.clicked.connect(lambda: self.deleteSeries())
        self.ui.generateButton.clicked.connect(lambda: self.generateGraph())
        self.ui.checkButton_1.clicked.connect(
            lambda: self.checkBasicData(
                self.ui.basicDataLineEdit.text()))
        self.ui.checkButton_2.clicked.connect(
            lambda: self.checkAllStock(
                self.ui.allStockLineEdit.text()))
        self.ui.checkButton_3.clicked.connect(
            lambda: self.checkStockData(
                self.ui.stockDataLineEdit.text()))
        self.ui.checkButton_4.clicked.connect(
            lambda: self.checkStatistic(
                self.ui.statisticLineEdit.text()))
        self.ui.checkButton_5.clicked.connect(
            lambda: self.checkClassified(
                self.ui.classifiedLineEdit.text()))
        self.ui.bulidButton_1.clicked.connect(lambda: self.buildBasicData())
        self.ui.bulidButton_2.clicked.connect(lambda: self.bulidAllStock())
        self.ui.bulidButton_3.clicked.connect(lambda: self.bulidStockData())
        self.ui.bulidButton_4.clicked.connect(lambda: self.bulidStatistic())
        self.ui.bulidButton_5.clicked.connect(lambda: self.bulidClassified())

        # 加载生成的统计图表
        local_url = QUrl.fromLocalFile(RENDER_FILE)
        self.ui.graphWidget.load(local_url)

    def outputWritten(self, text):
        if text != '':
            self.ui.outputLabel.setText(text)

    def isExistSeries(self, series):
        for i in range(self.ui.serieslistWidget.count()):
            if self.ui.serieslistWidget.item(i).text() == series:
                return True
                break
        return False

    def deleteSeries(self):
        self.ui.serieslistWidget.takeItem(
            self.ui.serieslistWidget.currentRow())

    def addSeries(self, tag, name, method, series):
        ss = '%s-%s-%s-%s' % (tag, name, method, series)
        if not self.isExistSeries(ss):
            self.ui.serieslistWidget.addItems([ss])

    def saveSeries(self):
        items = list()
        filename, ok = QFileDialog.getSaveFileName(
            self, '保存文件', iwencai.ROOT_DIR, '图表序列文件(*.srs)')
        if ok:
            f = open(filename, 'wb')
            for i in range(self.ui.serieslistWidget.count()):
                items += [self.ui.serieslistWidget.item(i).text()]
            pickle.dump(items, f)
            print('保存图表序列 %s' % filename, end='')

    def loadSeries(self):
        filename, ok = QFileDialog.getOpenFileName(
            self, '选取文件', iwencai.ROOT_DIR, '图表序列文件(*.srs)')
        if ok:
            f = open(filename, 'rb')
            items = pickle.load(f)
            self.ui.serieslistWidget.clear()
            for i in items:
                self.ui.serieslistWidget.addItem(i)
            print('加载图表序列 %s' % filename, end='')

    def checkBasicData(self, basicDataDir):
        if not os.path.isdir(basicDataDir):
            os.makedirs(basicDataDir)
        fl = [x for x in os.listdir(basicDataDir) if os.path.splitext(x)[
            1] == '.data']
        self.ui.basicDataLabel.setText(
            '<span style=" color:#ff0000;">包含数据文件%s-%s，共%d个。</span>' % (fl[0], fl[-1], len(fl)))

    def checkStockData(self, stockDataDir):
        if not os.path.isdir(stockDataDir):
            os.makedirs(stockDataDir)
        fl = [x for x in os.listdir(stockDataDir) if os.path.splitext(x)[
            1] == '.data']
        self.ui.stockDataLabel.setText(
            '<span style=" color:#ff0000;">包含数据文件%s-%s，共%d个。</span>' % (fl[0], fl[-1], len(fl)))

    def checkAllStock(self, allStockFile):
        if not os.path.exists(allStockFile):
            QMessageBox.information(
                self, '提示', '整合数据文件%s不存在，请重建！' %
                allStockFile, QMessageBox.Yes)
        df = iwencai.load_Snapshot(allStockFile)
        self.ui.allStockLabel.setText(
            '<span style=" color:#ff0000;">包含数据%d行 X %d列数据。</span>' %
            (len(df), len(
                df.columns)))

    def checkStatistic(self, statisticFile):
        if not os.path.exists(statisticFile):
            QMessageBox.information(
                self, '提示', '个股统计数据文件%s不存在，请重建！' %
                statisticFile, QMessageBox.Yes)
        df = iwencai.load_Snapshot(statisticFile)
        self.ui.statisticLabel.setText(
            '<span style=" color:#ff0000;">包含数据%d行 X %d列数据。</span>' %
            (len(df), len(
                df.columns)))

    def checkClassified(self, classifiedFile):
        if not os.path.exists(classifiedFile):
            QMessageBox.information(
                self, '提示', '行业统计数据文件%s不存在，请重建！' %
                classifiedFile, QMessageBox.Yes)
        df = iwencai.load_Snapshot(classifiedFile)
        self.ui.classifiedLabel.setText(
            '<span style=" color:#ff0000;">包含数据%d行 X %d列数据。</span>' %
            (len(df), len(
                df.columns)))

    def buildBasicData(self):
        _thread = Thread(
            target=iwencai.build_local_Snapshot,
            args=(
                iwencai.get_TradeDate()[0],
                iwencai.QUERY_COLUMN))
        _thread.start()

    def bulidStockData(self):
        _thread = Thread(target=iwencai.split_stock_Snapshot, args=())
        _thread.start()

    def bulidAllStock(self):
        _thread = Thread(target=iwencai.build_stock_Snapshot, args=())
        _thread.start()

    def bulidStatistic(self):
        _thread = Thread(target=iwencai.build_statistic_Snapshot, args=())
        _thread.start()

    def bulidClassified(self):
        _thread = Thread(target=iwencai.build_classified_Snapshot, args=())
        _thread.start()

    def generateGraph(self):
        if self.ui.serieslistWidget.count() == 0:
            return

        layout = go.Layout(xaxis=dict(
            tickformat='%Y-%m-%d',
            rangeselector=dict(buttons=list([
                dict(count=1, label='1月', step='month', stepmode='backward'),
                dict(count=6, label='6月', step='month', stepmode='backward'),
                dict(count=1, label='1年', step='year', stepmode='todate'),
                dict(count=5, label='5年', step='year', stepmode='backward'),
                dict(count=10, label='10年', step='year', stepmode='backward'),
                dict(label='显示所有', step='all')
            ])),
            rangeslider=dict(visible=True),
            type='date',
            title='时间'),
            yaxis=dict(),
            yaxis2=dict(
                title='yaxis2 title',
                overlaying='y',
                side='right')
        )

        out_M = pd.DataFrame()
        out_C = pd.DataFrame()
        out_S = pd.DataFrame()

        statistic = iwencai.load_Snapshot(iwencai.STATISTIC_FILE)
        classified = iwencai.load_Snapshot(iwencai.CLASSIFIED_FILE)
        data = []
        start = self.ui.startDateEdit.text().replace('/', '')
        end = self.ui.endDateEdit.text().replace('/', '')
        for i in range(self.ui.serieslistWidget.count()):
            series = self.ui.serieslistWidget.item(i).text().split('-', 3)
            method = iwencai.get_method_by_name(series[2])
            if series[0] == 'M':
                out_M = statistic[(statistic['market'] == series[1]) & (statistic['date'] > start) & (
                    statistic['date'] < end) & (statistic.index == method)][['date', series[3]]]
                out_M['date'] = pd.to_datetime(out_M['date'])
                index = out_M['date']
                value = out_M[series[3]]
                name = '%s-%s(%s)' % (series[2], series[3], series[1])
                data.append(go.Scatter(x=index, y=value,
                                       name=name, showlegend=True))

            elif series[0] == 'C':
                out_C = classified[(classified['行业'] == series[1]) & (classified[('date', '')] > start) & (
                    classified[('date', '')] < end)][[('date', ''), (series[3], method)]]
                out_C[('date', '')] = pd.to_datetime(out_C[('date', '')])
                index = out_C[('date', '')]
                value = out_C[(series[3], method)]
                name = '%s-%s(%s)' % (series[2], series[3], series[1])
                data.append(go.Scatter(x=index, y=value,
                                       name=name, showlegend=True))

            elif series[0] == 'S':
                stock = iwencai.load_Snapshot(
                    '%s/%s.data' % (iwencai.STOCK_DATA_DIR, series[1]))
                out_S = stock[(stock['date'] > start) & (
                    stock['date'] < end)][['date', series[3]]]

                out_S['date'] = pd.to_datetime(out_S['date'])
                index = out_S['date']
                value = out_S[series[3]]
                name = '%s-%s(%s)' % (series[2], series[3], series[1])
                data.append(go.Scatter(x=index, y=value,
                                       name=name, showlegend=True))

        layout['yaxis']['title'] = data[0]['name']
        if len(data) > 1:
            data[1]['yaxis'] = 'y2'
            layout['yaxis2']['title'] = data[1]['name']

        fig = go.Figure(data=data, layout=layout)

        config = {'scrollZoom': True, 'editable': True, 'displaylogo': False,
                  'modeBarButtonsToRemove': ['sendDataToCloud']}
        plotly.offline.plot(
            fig,
            filename=RENDER_FILE,
            auto_open=False,
            show_link=False,
            config=config, image='jpeg')

        self.ui.graphWidget.reload()
        self.ui.graphWidget.repaint()
        self.ui.graphWidget.update()


if not QApplication.instance():
    app = QApplication(sys.argv)
else:
    app = QApplication.instance()
w = MyUi()
w.show()
sys.exit(app.exec_())
