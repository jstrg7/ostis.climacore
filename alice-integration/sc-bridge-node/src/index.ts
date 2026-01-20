import express from 'express';
import bodyParser from 'body-parser';
import { connectSc } from './sc/client';
import { askQuestion } from './sc/commands';

const app = express();
app.use(bodyParser.json());

app.post('/sc/query', async (req, res) => {
  const { action, device, value, text } = req.body;

  try {

    if (action === 'ask') {
      const answer = await askQuestion(text);
      return res.json({ text: answer });
    }

    res.status(400).json({ error: 'unknown action' });
  } catch (e) {
    console.error(e);
    res.status(500).json({ error: 'sc error' });
  }
});

connectSc().then(() => {
  app.listen(3000, () => {
    console.log('🚀 sc-bridge-node on port 3000');
  });
});
