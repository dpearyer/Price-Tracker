const express = require('express');
const bodyParser = require('body-parser');
const { exec } = require('child_process'); 

const app = express();
const PORT = 5000;

app.use(bodyParser.json());

app.post('/track-price', (req, res) => {
    const { url } = req.body;

    if (!url) {
        return res.status(400).json({ success: false, message: 'URL is required' });
    }

    exec(`python track_price.py "${url}"`, (err, stdout, stderr) => {
        if (err) {
            console.error(`exec error: ${err}`);
            return res.status(500).json({ success: false, message: 'Internal server error' });
        }

        return res.json({ success: true, message: 'Price tracking started' });
    });
});

app.listen(PORT, () => {
    console.log(`Server running on http://localhost:${PORT}`);
});
