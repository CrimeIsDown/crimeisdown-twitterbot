var fs = require('fs'),
    Twit = require('twit'),
    async = require('async');

var T = null,
    livestreams = null;

start();

function start() {
    console.log('Initializing bot...');
    initTwit();
}

function end(error) {
    if (error) console.error(error);
    process.exit(1);
}

function initTwit() {
    fs.readFile('config.json', 'utf-8', function (err, fileContents) {
        if (err) {
            if (process.env.CONSUMER_KEY && process.env.CONSUMER_SECRET && process.env.ACCESS_TOKEN && process.env.ACCESS_TOKEN_SECRET) {
                T = new Twit({
                    "consumer_key": process.env.CONSUMER_KEY,
                    "consumer_secret" : process.env.CONSUMER_SECRET,
                    "access_token": process.env.ACCESS_TOKEN,
                    "access_token_secret": process.env.ACCESS_TOKEN_SECRET
                });
            } else {
                end('Config cound not be loaded, startup cannot continue. Exiting...');
            }
        } else {
            T = new Twit(JSON.parse(fileContents));
        }
        listen(T);
    });
    fs.readFile('onlinestreams.json', 'utf-8', function (err, fileContents) {
        if (err) {
            end('Cannot find online streams data, startup cannot continue. Exiting...');
        }
        livestreams = JSON.parse(fileContents);
    });
}

function listen(T) {
    var stream = T.stream('user', {});

    console.log('Bot initialized successfully. Now streaming.');

    stream.on('tweet', function (tweet) {
        checkTweet(tweet);
    });
}

function checkTweet(tweet) {
    var matches = tweet.text.toLowerCase().match(/(((citywide |cw)[1,6])|((zone |z)(1[0-3]|[1-9])))|(^((main)|(englewood))$)/);
    if (matches) {
        async.each(tweet.text.toLowerCase().split(' '), function (value, callback) {
            if (value.indexOf(matches[0])>0 && value.indexOf('://')>0) callback('bad match');
            else callback();
        }, function (err) {
            if (!err) retweet(tweet, matches);
        });
    }
}

function retweet(tweet, matches) {
    var rt = ' - RT @' + tweet.user.screen_name + ': ' + tweet.text;
    if (rt.length < 51) {
        var channel = livestreams[matches[0].toUpperCase()
                                            .replace('ZONE ', 'Z')
                                            .replace('CITYWIDE ', 'CW')
                                            .replace('MAIN', 'CFD-Fire')
                                            .replace('ENGLEWOOD', 'CFD-Fire')];
        if (channel) {
            var statusupdate = 'LISTEN LIVE to ' + channel.shortname + ' at ' + channel.feedUrl + '/web' + rt;
            T.post('statuses/update', {
                status: statusupdate,
                in_reply_to_status_id: tweet.id_str
            }, function (err, data, response) {
                if (err) console.error(err);
                console.log(statusupdate);
            });
        }
    }
}
