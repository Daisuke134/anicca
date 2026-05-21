package cli

import (
	"fmt"

	"github.com/spf13/cobra"
)

var versionCmd = &cobra.Command{
	Use:   "version",
	Short: "Print the greenlight version",
	Run: func(cmd *cobra.Command, args []string) {
		fmt.Printf("greenlight %s\n", appVersion)
	},
}
