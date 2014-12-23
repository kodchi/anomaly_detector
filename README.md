# Anomaly Detector

Detect anomalies using exponentially-weighted moving averages and standard deviations.

### About
* Tested with python 3.4
* It's assumed that there is a column called 'Day' in each csv file.

### How to
* Install requirements
````
$ pip install -r requirements.txt
````

* Rename the file config.yaml.sample to config.yaml and update it.

* ````$ python detect.py````

* Since only the last value in each time series is checked whether
 it's an anomaly, this script is more useful when setup as a cron job.