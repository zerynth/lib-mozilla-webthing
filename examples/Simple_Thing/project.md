Simple_Thing
============

In this example a simple Thing is created and will be able to control a LED.
Properties, events and actions are exposed through the Mozilla Web of Things
API specifications.

We used a Xinabox ESP32 which has an onboard LED

See https://iot.mozilla.org/wot/#web-thing-rest-api for more informations.


## How to run this example

Edit the Wi-Fi informations at the beginning of `main.py`; compile and uplink
the project through Zerynth Studio and open the serial monitor. 

Your board will print out it's local IP address and an URL you can use to begin
with. E.g.: http://192.168.1.137/xinabox.

We'll be using `curl` command in a Linux terminal to easily test our API.


### Fetch Thing informations
```
$ curl http://192.168.8.137/xinabox

{
  "name": "Xinabox ESP32",
  "description": "My really cool Xinabox ESP32",
  "properties": {
    "led": {
      "label": "LED",
      "type": "boolean",
      "readOnly": false,
      "description": "A LED which can be turned ON or OFF",
      "links": [
        {
          "href": "/xinabox/properties/led"
        }
      ]
    }
  },
  "actions": {
    "led": {
      "label": "LED",
      "description": "A LED which can be turned ON or OFF",
      "input": {
        "type": null
      }
    }
  },
  "events": {
    "led_change": {
      "description": "LED changed status"
    }
  },
  "links": [
    {
      "rel": "properties",
      "href": "/xinabox/properties"
    },
    {
      "rel": "actions",
      "href": "/xinabox/actions"
    },
    {
      "rel": "events",
      "href": "/xinabox/events"
    }
  ]
}
```


### Fetch current LED status
```
$ curl http://192.168.8.137/xinabox/properties

{
  "led": true
}
```


### Turn LED on/off
```
$ curl -XPUT -H 'Content-Type: application/json' -d '{ "led": false }' http://192.168.8.137/xinabox/properties/led

{ "led": false }


$ curl -XPUT -H 'Content-Type: application/json' -d '{ "led": true }' http://192.168.8.137/xinabox/properties/led

{ "led": true }
```
