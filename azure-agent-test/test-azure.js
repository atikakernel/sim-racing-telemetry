import express from 'express';
const app = express();
app.get('/', (req, res) => res.send('Hello from Azure Test!'));
const PORT = 8080;
app.listen(PORT, '0.0.0.0', () => {
    console.log('Test app listening on ' + PORT);
});
