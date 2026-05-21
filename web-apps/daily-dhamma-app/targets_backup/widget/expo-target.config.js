/** @type {import('@bacons/apple-targets/app.plugin').ConfigFunction} */
module.exports = (config) => ({
  type: "widget",
  name: "Daily Dhamma",
  deploymentTarget: "17.0",
  colors: {
    $accent: "#8B7355",
    $widgetBackground: "#F5F0E8",
  },
  entitlements: {
    "com.apple.security.application-groups": ["group.com.dailydhamma.app"]
  }
});
