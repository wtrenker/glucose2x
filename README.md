# glucose2

A Python, Sqlite, and Matplotlib project to chart my daily blood glucose levels. I am using the Caddy webserver to front-end the web site. Caddy is an https server that uses opensource security certificates.  It is a production-grade server written in the Go programming language. I am also using this project to delve into the Go language which i feel is about to spring onto the web app development scene.

This is the 2nd major version of the glucose software, which involves a significant refactoring. This new version supports tracking the average daily blood glucose reading over a long time period, ultimately years, not just months. Its live beginnings can be viewed at https://wtrenker.com. 

A major feature is that the chart is generated in real-time so when I update the database daily I don't have to do anything to replot the chart. This long term observation provides a means to watch the blood glucose trend as alternative medications are tried. An example, documented on the live chart, is the amazing improvement that Jardiance has made.
