package config

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"time"
)

// AuthMethod indicates how the user authenticated.
type AuthMethod string

const (
	AuthMethodAPIKey  AuthMethod = "api_key"
	AuthMethodSession AuthMethod = "session"
)

type Config struct {
	AuthMethod AuthMethod `json:"auth_method"`

	// API Key auth (App Store Connect API)
	KeyID          string `json:"key_id,omitempty"`
	IssuerID       string `json:"issuer_id,omitempty"`
	PrivateKeyPath string `json:"private_key_path,omitempty"`

	// Session auth (Apple ID)
	Session *SessionConfig `json:"session,omitempty"`
}

type SessionConfig struct {
	AppleID    string              `json:"apple_id"`
	SessionID  string              `json:"session_id"`
	Scnt       string              `json:"scnt"`
	Cookies    []*SerializedCookie `json:"cookies"`
	TeamID     string              `json:"team_id,omitempty"`
	ProviderID string              `json:"provider_id,omitempty"`
	ExpiresAt  time.Time           `json:"expires_at"`
}

type SerializedCookie struct {
	Name   string `json:"name"`
	Value  string `json:"value"`
	Domain string `json:"domain"`
	Path   string `json:"path"`
}

func ConfigDir() (string, error) {
	home, err := os.UserHomeDir()
	if err != nil {
		return "", err
	}
	return filepath.Join(home, ".greenlight"), nil
}

func configPath() (string, error) {
	dir, err := ConfigDir()
	if err != nil {
		return "", err
	}
	return filepath.Join(dir, "config.json"), nil
}

func Load() (*Config, error) {
	path, err := configPath()
	if err != nil {
		return nil, err
	}

	data, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("not authenticated — run 'greenlight auth login' or 'greenlight auth setup': %w", err)
	}

	var cfg Config
	if err := json.Unmarshal(data, &cfg); err != nil {
		return nil, fmt.Errorf("invalid config: %w", err)
	}

	return &cfg, nil
}

// IsValid checks if the config has usable credentials.
func (c *Config) IsValid() bool {
	switch c.AuthMethod {
	case AuthMethodAPIKey:
		return c.KeyID != "" && c.IssuerID != "" && c.PrivateKeyPath != ""
	case AuthMethodSession:
		return c.Session != nil && c.Session.SessionID != "" && time.Now().Before(c.Session.ExpiresAt)
	default:
		return false
	}
}

func Save(cfg *Config) error {
	dir, err := ConfigDir()
	if err != nil {
		return err
	}

	if err := os.MkdirAll(dir, 0700); err != nil {
		return err
	}

	data, err := json.MarshalIndent(cfg, "", "  ")
	if err != nil {
		return err
	}

	path := filepath.Join(dir, "config.json")
	return os.WriteFile(path, data, 0600)
}
