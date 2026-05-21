package codescan

// Severity levels matching the checks package.
type Severity int

const (
	SeverityInfo     Severity = iota // Best practice
	SeverityWarn                     // High risk
	SeverityCritical                 // Almost certain rejection
)

func (s Severity) String() string {
	switch s {
	case SeverityInfo:
		return "INFO"
	case SeverityWarn:
		return "WARN"
	case SeverityCritical:
		return "CRITICAL"
	default:
		return "UNKNOWN"
	}
}

// Finding is a single issue found in code.
type Finding struct {
	Severity  Severity `json:"severity"`
	Guideline string   `json:"guideline"`
	Title     string   `json:"title"`
	Detail    string   `json:"detail"`
	Fix       string   `json:"fix,omitempty"`
	File      string   `json:"file"`
	Line      int      `json:"line"` // 1-indexed
	Code      string   `json:"code,omitempty"`
}

// Rule is a code pattern check.
type Rule interface {
	// Applies returns true if this rule should run on the given file.
	Applies(fc FileContext) bool
	// Check runs the rule and returns any findings.
	Check(fc FileContext) []Finding
}

// GlobalAntiPatternRule is implemented by rules that suppress findings when
// anti-patterns are found anywhere in the project (not just the current file).
type GlobalAntiPatternRule interface {
	Rule
	// HasGlobalAntiPatterns returns true if this rule uses project-wide anti-pattern suppression.
	HasGlobalAntiPatterns() bool
	// AntiPatternMatched returns true if any anti-pattern matches the given file.
	AntiPatternMatched(fc FileContext) bool
	// RuleID returns the rule identifier.
	RuleID() string
}

// Summary holds aggregate results.
type Summary struct {
	Total     int  `json:"total"`
	Critical  int  `json:"critical"`
	Warns     int  `json:"warns"`
	Infos     int  `json:"infos"`
	FilesRead int  `json:"files_scanned"`
	Passed    bool `json:"passed"`
}

func ComputeSummary(findings []Finding, filesScanned int) Summary {
	s := Summary{FilesRead: filesScanned}
	for _, f := range findings {
		s.Total++
		switch f.Severity {
		case SeverityCritical:
			s.Critical++
		case SeverityWarn:
			s.Warns++
		case SeverityInfo:
			s.Infos++
		}
	}
	s.Passed = s.Critical == 0
	return s
}
