# glucose2

A Python, Sqlite, and Matplotlib project to chart my daily blood glucose levels. I am using the caddy webserver to front-end the web site with an https server that uses opensource security certificates.  I am also using this project to delve into the Go programming language which i feel is about to spring onto the web app development scene.

This is the 2nd major version of the software, which involves a significant refactoring. This new version supports tracking the average daily blood glucose reading over a long time period, e.g. years, not just months. It's live beginnings can be viewed at https://wtrenker.com . A major feature is that the chart is generated in real-time so when I update the database I don't have to do anything to replot the chart.

This long term observation provides a means to watch the blood glucose trend as alternative medications are tried. An example, documented on the live chart, is the amazing inprovement that Jardiance has made.
