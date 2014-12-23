#!/usr/bin/env python
# -*- coding: utf-8 -*-
import csv
from itertools import izip_longest
import os
import smtplib
import urllib2

# import matplotlib.pyplot as plt
from pycast.common import TimeSeries
from pycast.errors import MeanAbsolutePercentageError
from pycast.methods.exponentialsmoothing import HoltWintersMethod
import yaml


class AnomalyDetector():
    def __init__(self):
        self.config = {}
        self.load_config(os.path.join(os.path.curdir, 'config.yaml'))

    def load_config(self, config_path):
        """Load config"""
        with open(config_path) as config_file:
            self.config.update(yaml.load(config_file))

    def detect(self):
        """Detect anomalies and send an email."""
        anomalies = []
        for file_url in self.config['input']['data']:
            url_parts = file_url.rsplit('/', 1)
            file_name = url_parts[1].split('.')[0] if len(url_parts) == 2 else url_parts[0]
            try:
                response = urllib2.urlopen(file_url)
                reader = csv.reader(response)
                headers = reader.next()
                cache = {}
                forecasts = {}
                errors = {}
                for header in headers:
                    cache[header] = []
                    forecasts[header] = []
                for row in reader:
                    # store in cache only if the row is full or something other than null values
                    if not all([not a for a in row[1:]]):
                        for i, column in enumerate(row):
                            cache[headers[i]].append(column)
            except Exception, e:
                print('Error: Could not fetch the file %s: %s' % (file_url, e))
                continue

            observation_count = len(cache['Day'])
            for header, data in cache.items():
                if header == 'Day':
                    continue

                # TODO: remove this, but without it `division by 0` error occurs below in es.execute
                data = [1 if x == '0' else x for x in data]
                ts = TimeSeries.from_twodim_list(zip(cache['Day'], data), '%Y-%m-%d')

                # Calculate forecasts
                # The values of alpha, beta, and gamma below are not set in stone.
                # But they are producing good results now.
                # Feel free to change if the script results in wrong anomalies.
                # TODO: maybe allow alpha, beta, gamma, and period to be configurable?
                es = HoltWintersMethod(smoothingFactor=.9, trendSmoothingFactor=0.5,
                                       seasonSmoothingFactor=0.1, seasonLength=7)  # 7 days seems reasonable, no?
                forecast = es.execute(ts)
                forecasts[header] = [int(x[1]) if type(x[1]) == float else x[1] for x in forecast[:observation_count]]

                # Calculate difference between forecast and actual data
                mape = MeanAbsolutePercentageError()
                errors[header] = []
                for j, value in enumerate(ts):
                    local_error = mape.local_error([value[1]], [forecast[j][1]])
                    errors[header].append(int(local_error) if type(local_error) == float else local_error)

            # order columns
            forecast_values = []
            error_values = []
            for header in headers:
                if header == 'Day':
                    forecast_values.append(cache['Day'])
                    error_values.append(cache['Day'])
                else:
                    forecast_values.append(forecasts[header])
                    error_values.append(errors[header])

            # save to csv
            self.save_data_as_csv('%s-forecast' % file_name, headers, list(izip_longest(*forecast_values)))
            self.save_data_as_csv('%s-error' % file_name, headers, list(izip_longest(*error_values)))

            # # Graph - install matplotlib ;)
            # forecast_line, = plt.plot(forecasts['Home'], label='Forecast')
            # actual_line, = plt.plot(cache['Home'], label='Actual')
            # plt.legend(handles=[forecast_line, actual_line])
            # plt.savefig("graph.png")

            # Select errors that are bigger than the threshold
            anomaly = {
                'day': cache['Day'][observation_count - 1],
                'graph': file_name,
                'headers': []
            }
            for header, error in errors.items():
                if len(error) >= observation_count and error[observation_count - 1] >= self.config['error_threshold']:
                    anomaly['headers'].append(header)

            anomalies.append(anomaly)

        # send email about the last observation
        self.send_email(anomalies)

    def get_csv_filename(self, key):
        output_path = self.config['output']['path']
        if not os.path.exists(output_path):
            os.makedirs(output_path)
        return os.path.join(output_path, key + '.csv')

    def save_data_as_csv(self, key, headers, rows):
        # print(rows)
        csv_filename = self.get_csv_filename(key)
        with open(csv_filename, 'wb') as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(headers)
            writer.writerows(rows)

    def send_email(self, anomalies):
        """Send email about anomalies"""
        if len(anomalies) == 0:
            return

        messages = []
        for anomaly in anomalies:
            messages.append('Day: %s\nGraph: %s\nColumns: %s\n\n' %
                            (anomaly['day'], anomaly['graph'], ', '.join(anomaly['headers'])))

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
