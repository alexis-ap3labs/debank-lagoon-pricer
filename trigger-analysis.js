async function triggerAnalysis(config) {
  const GITHUB_TOKEN = 'your-github-token'; // À stocker de manière sécurisée
  const REPO_OWNER = 'your-username';
  const REPO_NAME = 'debank-usdc';

  const response = await fetch(
    `https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/dispatches`,
    {
      method: 'POST',
      headers: {
        'Accept': 'application/vnd.github.v3+json',
        'Authorization': `token ${GITHUB_TOKEN}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        event_type: 'run_analysis',
        client_payload: {
          config: JSON.stringify(config)
        }
      })
    }
  );

  if (!response.ok) {
    throw new Error('Failed to trigger analysis');
  }

  return response.json();
}

// Exemple d'utilisation :
const config = {
  wallet_address: "0x...",
  vault_address: "0x...",
  asset: {
    ticker: "USDC",
    coingecko_id: "usd-coin"
  },
  database_name: "your-database-name"
};

// Appel de la fonction
triggerAnalysis(config)
  .then(() => console.log('Analysis triggered successfully'))
  .catch(error => console.error('Error:', error)); 