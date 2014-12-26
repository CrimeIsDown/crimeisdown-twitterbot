var fs = require('fs'),
    Twit = require('twit');

var T = null;

start();

function start() {
    console.log('Initializing bot...');
    initConfig();
}

function initConfig() {
    console.log('Initializing config...');
    fs.readFile('config.json', 'utf-8', function (err, fileContents) {
        var config = null;
        if (err) {
            console.error('config.json not found, trying environment variables...');
            // use environment variables
            try {
                config = {
                    "consumer_key": process.env.CONSUMER_KEY,
                    "consumer_secret" : process.env.CONSUMER_SECRET,
                    "access_token": process.env.ACCESS_TOKEN,
                    "access_token_secret": process.env.ACCESS_TOKEN_SECRET
                };
            } catch (e) {
                console.error('Config cound not be loaded, startup cannot continue. Exiting...');
                process.exit(1);
            }
        } else {
            JSON.parse(fileContents);
        }
        initTwit(config);
    });
}

function initTwit(config) {
    console.log('Initializing Twitter API...');
    T = new Twit({
        consumer_key:         config.consumer_key,
        consumer_secret:      config.consumer_secret,
        access_token:         config.access_token,
        access_token_secret:  config.access_token_secret
    });
    listen(T);
}

function listen(T) {
    console.log('Initializing bot data and starting stream...');
    fs.readFile('onlinestreams.json', 'utf-8', function (err, fileContents) {
        if (err) {
            console.error('Cannot find online streams data, startup cannot continue. Exiting...');
            process.exit(1);
        }

        livestreams = JSON.parse(fileContents)
        var stream = T.stream('user', {});

        console.log('Bot initialized successfully. Now streaming.');

        stream.on('tweet', function (tweet) {
            checkTweet(tweet, livestreams);
        });
    });
}

function checkTweet(tweet, livestreams) {
    livestreams.forEach(function (channel, index) {
        if (tweet.text.toUpperCase().match('^[' + channel.shortname + '|ZONE ' + channel.shortname.replace('Z', '') + ']($| |,)')) {
            retweet(tweet, channel);
        }
    })
}

function retweet(tweet, channel) {
    var rt = ' - RT @' + tweet.user.screen_name + ': ' + tweet.text;
    var statusupdate = 'LISTEN LIVE to ' + (rt.length > 20 ? channel.shortname : channel.name) + ' at ' + channel.feedUrl + '/web' + (rt.length < 55 ? ' #ChicagoScanner' : '') + rt;
    T.post('statuses/update', {
        status: statusupdate,
        in_reply_to_status_id: tweet.id_str
    }, function (err, data, response) {
        if (err) console.error(err);
        console.log(statusupdate);
    });
}
