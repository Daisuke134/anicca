package guidelines

import (
	_ "embed"
	"encoding/json"
	"strings"
)

//go:embed data/guidelines.json
var guidelinesJSON []byte

// Guideline represents a single Apple review guideline.
type Guideline struct {
	Section          string      `json:"section"`
	Title            string      `json:"title"`
	Content          string      `json:"content"`
	CommonViolations []string    `json:"common_violations,omitempty"`
	Subsections      []Guideline `json:"subsections,omitempty"`
}

// DB holds the full set of guidelines for querying.
type DB struct {
	Guidelines []Guideline `json:"guidelines"`
	index      map[string]*Guideline
}

// Load parses the embedded guidelines JSON.
func Load() (*DB, error) {
	var db DB
	if err := json.Unmarshal(guidelinesJSON, &db); err != nil {
		return nil, err
	}
	db.buildIndex()
	return &db, nil
}

func (db *DB) buildIndex() {
	db.index = make(map[string]*Guideline)
	var walk func(gs []Guideline)
	walk = func(gs []Guideline) {
		for i := range gs {
			db.index[gs[i].Section] = &gs[i]
			walk(gs[i].Subsections)
		}
	}
	walk(db.Guidelines)
}

// Get returns a guideline by section number (e.g. "2.1", "5.1.1").
func (db *DB) Get(section string) (*Guideline, bool) {
	g, ok := db.index[section]
	return g, ok
}

// TopLevel returns the 5 top-level guideline sections.
func (db *DB) TopLevel() []Guideline {
	return db.Guidelines
}

// Search finds guidelines matching a keyword query.
func (db *DB) Search(query string) []Guideline {
	query = strings.ToLower(query)
	var results []Guideline

	var walk func(gs []Guideline)
	walk = func(gs []Guideline) {
		for _, g := range gs {
			if strings.Contains(strings.ToLower(g.Title), query) ||
				strings.Contains(strings.ToLower(g.Content), query) ||
				strings.Contains(strings.ToLower(g.Section), query) {
				results = append(results, g)
			}
			walk(g.Subsections)
		}
	}
	walk(db.Guidelines)

	return results
}
