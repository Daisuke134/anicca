export default async function handler(req, res) {

  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    return res.status(200).json({});
  } catch (error) {
    console.error('Error fetching MCP config:', error);
    return res.status(500).json({ error: 'Internal server error' });
  }
}
