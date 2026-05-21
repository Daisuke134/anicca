/**
 * Agent Authentication Middleware
 * 
 * Validates ANICCA_AGENT_TOKEN (separate from INTERNAL_API_TOKEN)
 * Supports token rotation with ANICCA_AGENT_TOKEN_OLD during grace period
 */

const AGENT_TOKEN = process.env.ANICCA_AGENT_TOKEN;
const AGENT_TOKEN_OLD = process.env.ANICCA_AGENT_TOKEN_OLD;

/**
 * @param {import('express').Request} req
 * @param {import('express').Response} res
 * @param {import('express').NextFunction} next
 */
export function requireAgentAuth(req, res, next) {
  const authHeader = req.headers.authorization;

  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    return res.status(401).json({
      error: 'Unauthorized',
      message: 'Missing or invalid Authorization header',
    });
  }

  const token = authHeader.slice(7); // Remove 'Bearer '

  // Validate against current token OR old token (rotation grace period)
  const isValidToken = token === AGENT_TOKEN || (AGENT_TOKEN_OLD && token === AGENT_TOKEN_OLD);

  if (!isValidToken) {
    return res.status(401).json({
      error: 'Unauthorized',
      message: 'Invalid agent token',
    });
  }

  // Attach token info to request for audit logging
  req.agentAuth = {
    tokenType: token === AGENT_TOKEN ? 'current' : 'legacy',
    authenticatedAt: new Date().toISOString(),
  };

  next();
}

export default requireAgentAuth;
