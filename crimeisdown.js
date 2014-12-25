var Twit = require('twit'),
    fs = require('fs');

var T = null;

start();

function start() {
    initConfig();
}

function initConfig() {
    fs.readFile('config.json', 'utf-8', function (err, fileContents) {
        if (err) throw err;
        initTwit(JSON.parse(fileContents));
    });
}

function initTwit(config) {
    T = new Twit({
        consumer_key:         config.consumer_key,
        consumer_secret:      config.consumer_secret,
        access_token:         config.access_token,
        access_token_secret:  config.access_token_secret
    });
    listen(T);
}

function listen(T) {
    fs.readFile('onlinestreams.json', 'utf-8', function (err, fileContents) {
        livestreams = JSON.parse(fileContents)
        var stream = T.stream('user', {});

        stream.on('tweet', function (tweet) {
            checkTweet(tweet, livestreams);
        });
    });
}

function checkTweet(tweet, livestreams) {
    livestreams.forEach(function (channel, index) {
        if (tweet.text.match('^' + channel.shortname + '$')) {
            retweet(tweet, channel);
        }
    })
}

function retweet(tweet, channel) {
    var statusupdate = 'LISTEN LIVE to ' + channel.name + ' at ' + channel.feedUrl + '/web #ChicagoScanner - RT @' + tweet.user.screen_name + ': ' + tweet.text;
    T.post('statuses/update', {
        status: statusupdate,
        in_reply_to_status_id: tweet.id
    }, function (err, data, response) {
        console.log(statusupdate);
    });
}
