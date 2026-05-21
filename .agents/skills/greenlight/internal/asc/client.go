package asc

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"
)

const baseURL = "https://api.appstoreconnect.apple.com/v1"

type Client struct {
	keyID      string
	issuerID   string
	keyPath    string
	httpClient *http.Client
	token      string
	tokenExp   time.Time
}

func NewClient(keyID, issuerID, privateKeyPath string) (*Client, error) {
	c := &Client{
		keyID:    keyID,
		issuerID: issuerID,
		keyPath:  privateKeyPath,
		httpClient: &http.Client{
			Timeout: 30 * time.Second,
		},
	}

	// Validate credentials by generating a token
	if err := c.refreshToken(); err != nil {
		return nil, err
	}

	return c, nil
}

func (c *Client) refreshToken() error {
	token, err := generateToken(c.keyID, c.issuerID, c.keyPath)
	if err != nil {
		return err
	}
	c.token = token
	c.tokenExp = time.Now().Add(15 * time.Minute) // refresh before 20min expiry
	return nil
}

func (c *Client) get(path string, result interface{}) error {
	if time.Now().After(c.tokenExp) {
		if err := c.refreshToken(); err != nil {
			return err
		}
	}

	url := baseURL + path
	req, err := http.NewRequest("GET", url, nil)
	if err != nil {
		return err
	}
	req.Header.Set("Authorization", "Bearer "+c.token)

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return fmt.Errorf("API request failed: %w", err)
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return fmt.Errorf("failed to read response: %w", err)
	}

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("API error %d: %s", resp.StatusCode, string(body))
	}

	if result != nil {
		if err := json.Unmarshal(body, result); err != nil {
			return fmt.Errorf("failed to parse response: %w", err)
		}
	}

	return nil
}
