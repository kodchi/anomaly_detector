import argparse
from email.mime.text import MIMEText
import json
import smtplib
import os
import pandas as pd
import yaml


class AnomalyDetector():
    def __init__(self):
        self.config = {}
        self.load_config(os.path.join(os.path.curdir, 'config.yaml'))

    def load_config(self, config_path):
        """Load config"""
        with open(config_path, encoding='utf-8') as config_file:
            self.config.update(yaml.load(config_file))

    def detect(self):
        """
        If a value is more than 3 exponentially-weighted moving standard deviations
        away from the exponentially-weighted moving average then it is considered
        an anomaly.
        """
        anomalies = []
        for graph_name, file_name in self.config['input']['data']:
            graph_anomalies = []
            data = pd.read_csv(
                os.path.join(self.config['input']['path'], file_name)
            )
            day = data['Day'].tail(1).values[0]
            for column_name in data.columns:
                # some fields, for example Day, cannot be converted to floats
                try:
                    last_value = data[column_name].tail(1).tail(1).values[0]
                    ewma = pd.ewma(data[column_name], span=15).tail(1).values[0]
                    ewmstd = pd.ewmstd(data[column_name], span=15).tail(1).values[0]
                except ValueError as e:
                    print("Error in graph %s, column %s: %s" % (graph_name, column_name, e))
                    continue
                if last_value < ewma - 3 * ewmstd or \
                        last_value > ewma + 3 * ewmstd:
                    graph_anomalies.append(column_name)

            if len(graph_anomalies):
                anomalies.append((day, graph_name, graph_anomalies))

        self.send_email(anomalies)

    def send_email(self, anomalies):
        """Send email about anomalies"""
        if not len(anomalies):
            return

        messages = []
        for anomaly in anomalies:
            messages.append('Day: %s\nGraph: %s\nColumns: %s\n\n' %
                            (anomaly[0], anomaly[1], ', '.join(anomaly[2])))

        message = """\From: %s\nTo: %s\nSubject: %s\n\n%s""" %\
                  (self.config['email']['user'],
                   ", ".join(self.config['email']['recipients']),
                   self.config['email']['subject'],
                   '\n'.join(messages))

        try:
            server = smtplib.SMTP(self.config['email']['host'], self.config['email']['port'])
            server.ehlo()
            server.starttls()
            server.login(self.config['email']['user'], self.config['email']['password'])
            server.sendmail(self.config['email']['user'], self.config['email']['recipients'], message)
            server.close()
            print('Successfully sent the mail.')
        except Exception as e:
            print("Error. Could not send the mail: %s\nEmail contents were:\n%s" % (e, message))


if __name__ == '__main__':
    ad = AnomalyDetector()
    ad.detect()
