package checks

import (
	"context"
	"fmt"

	"github.com/RevylAI/greenlight/internal/asc"
)

// Check is an individual compliance check function.
type Check func(ctx context.Context, client *asc.Client, appID string, findings *[]Finding) error

// Runner orchestrates all checks across tiers.
type Runner struct {
	client  *asc.Client
	verbose bool
	checks  map[Tier][]namedCheck
}

type namedCheck struct {
	name string
	fn   Check
}

func NewRunner(client *asc.Client, verbose bool) *Runner {
	r := &Runner{
		client:  client,
		verbose: verbose,
		checks:  make(map[Tier][]namedCheck),
	}
	r.registerChecks()
	return r
}

func (r *Runner) registerChecks() {
	// Tier 1: Metadata & completeness (API-based)
	r.register(TierMetadata, "App exists & accessible", checkAppExists)
	r.register(TierMetadata, "App name length", checkAppNameLength)
	r.register(TierMetadata, "Version prepared", checkVersionPrepared)
	r.register(TierMetadata, "Metadata completeness", checkMetadataCompleteness)
	r.register(TierMetadata, "Screenshots uploaded", checkScreenshots)
	r.register(TierMetadata, "Screenshot dimensions", checkScreenshotDimensions)
	r.register(TierMetadata, "Build processed", checkBuildProcessed)
	r.register(TierMetadata, "Age rating declared", checkAgeRating)
	r.register(TierMetadata, "Encryption compliance", checkEncryption)
	r.register(TierMetadata, "Territory availability", checkTerritoryAvailability)
	r.register(TierMetadata, "Pricing consistency", checkPricingConsistency)

	// Tier 2: Content analysis
	r.register(TierContent, "Platform references", checkPlatformReferences)
	r.register(TierContent, "Placeholder content", checkPlaceholderContent)
	r.register(TierContent, "URL reachability", checkURLReachability)
	r.register(TierContent, "TestFlight external testing", checkTestFlightExternal)
}

func (r *Runner) register(tier Tier, name string, fn Check) {
	r.checks[tier] = append(r.checks[tier], namedCheck{name: name, fn: fn})
}

// Run executes all checks up to the specified max tier.
func (r *Runner) Run(ctx context.Context, appID, buildNum string, maxTier int) (*Results, error) {
	results := &Results{
		AppID: appID,
	}

	for tier := TierMetadata; int(tier) <= maxTier; tier++ {
		checks, ok := r.checks[tier]
		if !ok {
			continue
		}

		for _, check := range checks {
			if r.verbose {
				fmt.Printf("  [tier %d] running: %s\n", tier, check.name)
			}

			if err := check.fn(ctx, r.client, appID, &results.Findings); err != nil {
				if r.verbose {
					fmt.Printf("  [tier %d] error in %s: %v\n", tier, check.name, err)
				}
				// Non-fatal: record as a finding rather than aborting
				results.Findings = append(results.Findings, Finding{
					Tier:     tier,
					Severity: SeverityWarn,
					Title:    fmt.Sprintf("Check '%s' failed to run", check.name),
					Detail:   err.Error(),
				})
			}
		}
	}

	results.ComputeSummary()
	return results, nil
}
