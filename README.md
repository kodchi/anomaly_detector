# Anomaly Detector

Detect anomalies using the Holt-Winters Method.

### About
* Tested with python 2.7.6
* It's assumed that there is a column called 'Day' in each csv file.

### How to
* Install requirements: ````$ pip install -r requirements.txt````

* Rename the file config.yaml.sample to config.yaml and update it.

* Run the script: ````$ python detect.py````

* The script generates two csv files for each input file: one with forecasted values,
 the other with Mean Absolute Percentage Error (between actual and forecasted values).
 
* The last value for Mean Absolute Percentage Error is then compared the the error threshold.
 Errors that are bigger than the threshold are considered anomalies and emailed to recipients.
 
 
### More info
* https://pythonhosted.org/pycast/methods/forecastingmethods.html
* http://static.usenix.org/events/lisa00/full_papers/brutlag/brutlag_html/
