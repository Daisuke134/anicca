
Object.defineProperty(exports, "__esModule", { value: true });

const {
  Decimal,
  objectEnumValues,
  makeStrictEnum,
  Public,
  getRuntime,
  skip
} = require('./runtime/index-browser.js')


const Prisma = {}

exports.Prisma = Prisma
exports.$Enums = {}

/**
 * Prisma Client JS version: 5.22.0
 * Query Engine version: 605197351a3c8bdd595af2d2a9bc3025bca48ea2
 */
Prisma.prismaVersion = {
  client: "5.22.0",
  engine: "605197351a3c8bdd595af2d2a9bc3025bca48ea2"
}

Prisma.PrismaClientKnownRequestError = () => {
  const runtimeName = getRuntime().prettyName;
  throw new Error(`PrismaClientKnownRequestError is unable to run in this browser environment, or has been bundled for the browser (running in ${runtimeName}).
In case this error is unexpected for you, please report it in https://pris.ly/prisma-prisma-bug-report`,
)};
Prisma.PrismaClientUnknownRequestError = () => {
  const runtimeName = getRuntime().prettyName;
  throw new Error(`PrismaClientUnknownRequestError is unable to run in this browser environment, or has been bundled for the browser (running in ${runtimeName}).
In case this error is unexpected for you, please report it in https://pris.ly/prisma-prisma-bug-report`,
)}
Prisma.PrismaClientRustPanicError = () => {
  const runtimeName = getRuntime().prettyName;
  throw new Error(`PrismaClientRustPanicError is unable to run in this browser environment, or has been bundled for the browser (running in ${runtimeName}).
In case this error is unexpected for you, please report it in https://pris.ly/prisma-prisma-bug-report`,
)}
Prisma.PrismaClientInitializationError = () => {
  const runtimeName = getRuntime().prettyName;
  throw new Error(`PrismaClientInitializationError is unable to run in this browser environment, or has been bundled for the browser (running in ${runtimeName}).
In case this error is unexpected for you, please report it in https://pris.ly/prisma-prisma-bug-report`,
)}
Prisma.PrismaClientValidationError = () => {
  const runtimeName = getRuntime().prettyName;
  throw new Error(`PrismaClientValidationError is unable to run in this browser environment, or has been bundled for the browser (running in ${runtimeName}).
In case this error is unexpected for you, please report it in https://pris.ly/prisma-prisma-bug-report`,
)}
Prisma.NotFoundError = () => {
  const runtimeName = getRuntime().prettyName;
  throw new Error(`NotFoundError is unable to run in this browser environment, or has been bundled for the browser (running in ${runtimeName}).
In case this error is unexpected for you, please report it in https://pris.ly/prisma-prisma-bug-report`,
)}
Prisma.Decimal = Decimal

/**
 * Re-export of sql-template-tag
 */
Prisma.sql = () => {
  const runtimeName = getRuntime().prettyName;
  throw new Error(`sqltag is unable to run in this browser environment, or has been bundled for the browser (running in ${runtimeName}).
In case this error is unexpected for you, please report it in https://pris.ly/prisma-prisma-bug-report`,
)}
Prisma.empty = () => {
  const runtimeName = getRuntime().prettyName;
  throw new Error(`empty is unable to run in this browser environment, or has been bundled for the browser (running in ${runtimeName}).
In case this error is unexpected for you, please report it in https://pris.ly/prisma-prisma-bug-report`,
)}
Prisma.join = () => {
  const runtimeName = getRuntime().prettyName;
  throw new Error(`join is unable to run in this browser environment, or has been bundled for the browser (running in ${runtimeName}).
In case this error is unexpected for you, please report it in https://pris.ly/prisma-prisma-bug-report`,
)}
Prisma.raw = () => {
  const runtimeName = getRuntime().prettyName;
  throw new Error(`raw is unable to run in this browser environment, or has been bundled for the browser (running in ${runtimeName}).
In case this error is unexpected for you, please report it in https://pris.ly/prisma-prisma-bug-report`,
)}
Prisma.validator = Public.validator

/**
* Extensions
*/
Prisma.getExtensionContext = () => {
  const runtimeName = getRuntime().prettyName;
  throw new Error(`Extensions.getExtensionContext is unable to run in this browser environment, or has been bundled for the browser (running in ${runtimeName}).
In case this error is unexpected for you, please report it in https://pris.ly/prisma-prisma-bug-report`,
)}
Prisma.defineExtension = () => {
  const runtimeName = getRuntime().prettyName;
  throw new Error(`Extensions.defineExtension is unable to run in this browser environment, or has been bundled for the browser (running in ${runtimeName}).
In case this error is unexpected for you, please report it in https://pris.ly/prisma-prisma-bug-report`,
)}

/**
 * Shorthand utilities for JSON filtering
 */
Prisma.DbNull = objectEnumValues.instances.DbNull
Prisma.JsonNull = objectEnumValues.instances.JsonNull
Prisma.AnyNull = objectEnumValues.instances.AnyNull

Prisma.NullTypes = {
  DbNull: objectEnumValues.classes.DbNull,
  JsonNull: objectEnumValues.classes.JsonNull,
  AnyNull: objectEnumValues.classes.AnyNull
}



/**
 * Enums
 */

exports.Prisma.TransactionIsolationLevel = makeStrictEnum({
  ReadUncommitted: 'ReadUncommitted',
  ReadCommitted: 'ReadCommitted',
  RepeatableRead: 'RepeatableRead',
  Serializable: 'Serializable'
});

exports.Prisma.TokenScalarFieldEnum = {
  userId: 'userId',
  provider: 'provider',
  providerSub: 'providerSub',
  email: 'email',
  accessTokenEnc: 'accessTokenEnc',
  refreshTokenEnc: 'refreshTokenEnc',
  scope: 'scope',
  expiry: 'expiry',
  rotationFamilyId: 'rotationFamilyId',
  revokedAt: 'revokedAt',
  createdAt: 'createdAt',
  updatedAt: 'updatedAt'
};

exports.Prisma.RefreshTokenScalarFieldEnum = {
  id: 'id',
  userId: 'userId',
  tokenHash: 'tokenHash',
  deviceId: 'deviceId',
  userAgent: 'userAgent',
  createdAt: 'createdAt',
  expiresAt: 'expiresAt',
  rotatedFrom: 'rotatedFrom',
  revokedAt: 'revokedAt',
  lastUsedAt: 'lastUsedAt',
  reuseDetected: 'reuseDetected'
};

exports.Prisma.MobileProfileScalarFieldEnum = {
  deviceId: 'deviceId',
  userId: 'userId',
  profile: 'profile',
  language: 'language',
  updatedAt: 'updatedAt',
  createdAt: 'createdAt'
};

exports.Prisma.UserSubscriptionScalarFieldEnum = {
  userId: 'userId',
  plan: 'plan',
  status: 'status',
  entitlementSource: 'entitlementSource',
  revenuecatEntitlementId: 'revenuecatEntitlementId',
  revenuecatOriginalTransactionId: 'revenuecatOriginalTransactionId',
  entitlementPayload: 'entitlementPayload',
  currentPeriodEnd: 'currentPeriodEnd',
  trialEnd: 'trialEnd',
  metadata: 'metadata',
  updatedAt: 'updatedAt'
};

exports.Prisma.SubscriptionEventScalarFieldEnum = {
  eventId: 'eventId',
  userId: 'userId',
  type: 'type',
  provider: 'provider',
  payload: 'payload',
  createdAt: 'createdAt'
};

exports.Prisma.MonthlyVcGrantScalarFieldEnum = {
  userId: 'userId',
  grantMonth: 'grantMonth',
  reason: 'reason',
  minutes: 'minutes',
  grantedAt: 'grantedAt'
};

exports.Prisma.ProfileScalarFieldEnum = {
  id: 'id',
  email: 'email',
  metadata: 'metadata',
  createdAt: 'createdAt',
  updatedAt: 'updatedAt'
};

exports.Prisma.UserSettingScalarFieldEnum = {
  userId: 'userId',
  language: 'language',
  timezone: 'timezone',
  notificationsEnabled: 'notificationsEnabled',
  nudgeDay0LocalDate: 'nudgeDay0LocalDate',
  nudgeDay0Source: 'nudgeDay0Source',
  preferences: 'preferences',
  createdAt: 'createdAt',
  updatedAt: 'updatedAt'
};

exports.Prisma.PushTokenScalarFieldEnum = {
  id: 'id',
  profileId: 'profileId',
  deviceId: 'deviceId',
  token: 'token',
  platform: 'platform',
  env: 'env',
  disabledAt: 'disabledAt',
  lastError: 'lastError',
  updatedAt: 'updatedAt',
  createdAt: 'createdAt'
};

exports.Prisma.NudgeDeliveryScalarFieldEnum = {
  id: 'id',
  profileId: 'profileId',
  problemType: 'problemType',
  scheduledTime: 'scheduledTime',
  deliveryDayLocal: 'deliveryDayLocal',
  timezone: 'timezone',
  lang: 'lang',
  variantIndex: 'variantIndex',
  quoteId: 'quoteId',
  messageTitle: 'messageTitle',
  messageBody: 'messageBody',
  messageDetail: 'messageDetail',
  status: 'status',
  apnsId: 'apnsId',
  error: 'error',
  attemptCount: 'attemptCount',
  lastAttemptAt: 'lastAttemptAt',
  nextAttemptAt: 'nextAttemptAt',
  createdAt: 'createdAt',
  sentAt: 'sentAt'
};

exports.Prisma.NudgeDeliverySendScalarFieldEnum = {
  id: 'id',
  deliveryId: 'deliveryId',
  pushTokenId: 'pushTokenId',
  status: 'status',
  apnsId: 'apnsId',
  error: 'error',
  attemptCount: 'attemptCount',
  lastAttemptAt: 'lastAttemptAt',
  nextAttemptAt: 'nextAttemptAt',
  sentAt: 'sentAt',
  updatedAt: 'updatedAt',
  createdAt: 'createdAt'
};

exports.Prisma.UserTraitScalarFieldEnum = {
  userId: 'userId',
  ideals: 'ideals',
  struggles: 'struggles',
  big5: 'big5',
  keywords: 'keywords',
  summary: 'summary',
  nudgeIntensity: 'nudgeIntensity',
  stickyMode: 'stickyMode',
  createdAt: 'createdAt',
  updatedAt: 'updatedAt'
};

exports.Prisma.NudgeEventScalarFieldEnum = {
  id: 'id',
  userId: 'userId',
  domain: 'domain',
  subtype: 'subtype',
  decisionPoint: 'decisionPoint',
  state: 'state',
  actionTemplate: 'actionTemplate',
  channel: 'channel',
  sent: 'sent',
  createdAt: 'createdAt'
};

exports.Prisma.NudgeOutcomeScalarFieldEnum = {
  id: 'id',
  nudgeEventId: 'nudgeEventId',
  reward: 'reward',
  shortTerm: 'shortTerm',
  emaScore: 'emaScore',
  signals: 'signals',
  createdAt: 'createdAt'
};

exports.Prisma.FeelingSessionScalarFieldEnum = {
  id: 'id',
  userId: 'userId',
  feelingId: 'feelingId',
  topic: 'topic',
  actionTemplate: 'actionTemplate',
  startedAt: 'startedAt',
  endedAt: 'endedAt',
  emaBetter: 'emaBetter',
  summary: 'summary',
  transcript: 'transcript',
  context: 'context',
  createdAt: 'createdAt'
};

exports.Prisma.BanditModelScalarFieldEnum = {
  id: 'id',
  domain: 'domain',
  version: 'version',
  weights: 'weights',
  covariance: 'covariance',
  meta: 'meta',
  createdAt: 'createdAt',
  updatedAt: 'updatedAt'
};

exports.Prisma.UserTypeEstimateScalarFieldEnum = {
  userId: 'userId',
  primaryType: 'primaryType',
  typeScores: 'typeScores',
  confidence: 'confidence',
  createdAt: 'createdAt',
  updatedAt: 'updatedAt'
};

exports.Prisma.TypeStatsScalarFieldEnum = {
  typeId: 'typeId',
  tone: 'tone',
  tappedCount: 'tappedCount',
  ignoredCount: 'ignoredCount',
  thumbsUpCount: 'thumbsUpCount',
  thumbsDownCount: 'thumbsDownCount',
  sampleSize: 'sampleSize',
  updatedAt: 'updatedAt'
};

exports.Prisma.HookCandidateScalarFieldEnum = {
  id: 'id',
  text: 'text',
  tone: 'tone',
  targetProblemTypes: 'targetProblemTypes',
  targetUserTypes: 'targetUserTypes',
  appTapRate: 'appTapRate',
  appThumbsUpRate: 'appThumbsUpRate',
  appSampleSize: 'appSampleSize',
  tiktokLikeRate: 'tiktokLikeRate',
  tiktokShareRate: 'tiktokShareRate',
  tiktokSampleSize: 'tiktokSampleSize',
  tiktokHighPerformer: 'tiktokHighPerformer',
  isWisdom: 'isWisdom',
  explorationWeight: 'explorationWeight',
  createdAt: 'createdAt',
  updatedAt: 'updatedAt',
  source: 'source',
  generatedForUserId: 'generatedForUserId',
  promoted: 'promoted',
  xEngagementRate: 'xEngagementRate',
  xSampleSize: 'xSampleSize',
  xHighPerformer: 'xHighPerformer',
  moltbookUpvoteRate: 'moltbookUpvoteRate',
  moltbookSampleSize: 'moltbookSampleSize',
  moltbookHighPerformer: 'moltbookHighPerformer',
  slackReactionRate: 'slackReactionRate',
  slackSampleSize: 'slackSampleSize',
  slackHighPerformer: 'slackHighPerformer'
};

exports.Prisma.TiktokPostScalarFieldEnum = {
  id: 'id',
  hookCandidateId: 'hookCandidateId',
  tiktokVideoId: 'tiktokVideoId',
  blotatoPostId: 'blotatoPostId',
  caption: 'caption',
  postedAt: 'postedAt',
  metricsFetchedAt: 'metricsFetchedAt',
  viewCount: 'viewCount',
  likeCount: 'likeCount',
  commentCount: 'commentCount',
  shareCount: 'shareCount',
  agentReasoning: 'agentReasoning',
  slot: 'slot',
  scheduledAt: 'scheduledAt',
  createdAt: 'createdAt'
};

exports.Prisma.WisdomPatternScalarFieldEnum = {
  id: 'id',
  patternName: 'patternName',
  description: 'description',
  targetUserTypes: 'targetUserTypes',
  effectiveTone: 'effectiveTone',
  effectiveHookPattern: 'effectiveHookPattern',
  effectiveContentLength: 'effectiveContentLength',
  appEvidence: 'appEvidence',
  tiktokEvidence: 'tiktokEvidence',
  confidence: 'confidence',
  verifiedAt: 'verifiedAt',
  createdAt: 'createdAt',
  updatedAt: 'updatedAt'
};

exports.Prisma.XPostScalarFieldEnum = {
  id: 'id',
  hookCandidateId: 'hookCandidateId',
  xPostId: 'xPostId',
  blotatoPostId: 'blotatoPostId',
  text: 'text',
  slot: 'slot',
  postedAt: 'postedAt',
  metricsFetchedAt: 'metricsFetchedAt',
  impressionCount: 'impressionCount',
  likeCount: 'likeCount',
  retweetCount: 'retweetCount',
  replyCount: 'replyCount',
  engagementRate: 'engagementRate',
  agentReasoning: 'agentReasoning',
  createdAt: 'createdAt'
};

exports.Prisma.NotificationScheduleScalarFieldEnum = {
  id: 'id',
  userId: 'userId',
  schedule: 'schedule',
  agentRawOutput: 'agentRawOutput',
  createdAt: 'createdAt'
};

exports.Prisma.AgentPostScalarFieldEnum = {
  id: 'id',
  platform: 'platform',
  externalPostId: 'externalPostId',
  platformUserId: 'platformUserId',
  severity: 'severity',
  region: 'region',
  hook: 'hook',
  content: 'content',
  tone: 'tone',
  problemType: 'problemType',
  reasoning: 'reasoning',
  buddhismReference: 'buddhismReference',
  upvotes: 'upvotes',
  reactions: 'reactions',
  views: 'views',
  likes: 'likes',
  shares: 'shares',
  comments: 'comments',
  moltbookZ: 'moltbookZ',
  slackZ: 'slackZ',
  tiktokZ: 'tiktokZ',
  xZ: 'xZ',
  instagramZ: 'instagramZ',
  unifiedScore: 'unifiedScore',
  createdAt: 'createdAt',
  updatedAt: 'updatedAt',
  promotedToHookCandidates: 'promotedToHookCandidates',
  anonymizedAt: 'anonymizedAt'
};

exports.Prisma.AgentAuditLogScalarFieldEnum = {
  id: 'id',
  eventType: 'eventType',
  agentPostId: 'agentPostId',
  platform: 'platform',
  requestPayload: 'requestPayload',
  responsePayload: 'responsePayload',
  executedBy: 'executedBy',
  durationMs: 'durationMs',
  createdAt: 'createdAt'
};

exports.Prisma.MemoryItemScalarFieldEnum = {
  id: 'id',
  scope: 'scope',
  category: 'category',
  key: 'key',
  value: 'value',
  confidence: 'confidence',
  source: 'source',
  expiresAt: 'expiresAt',
  createdAt: 'createdAt',
  updatedAt: 'updatedAt'
};

exports.Prisma.InitiativeScalarFieldEnum = {
  id: 'id',
  kind: 'kind',
  status: 'status',
  reason: 'reason',
  payload: 'payload',
  createdAt: 'createdAt',
  updatedAt: 'updatedAt'
};

exports.Prisma.ResearchItemScalarFieldEnum = {
  id: 'id',
  source: 'source',
  query: 'query',
  summary: 'summary',
  payload: 'payload',
  createdAt: 'createdAt'
};

exports.Prisma.OpsProposalScalarFieldEnum = {
  id: 'id',
  skillName: 'skillName',
  source: 'source',
  status: 'status',
  title: 'title',
  payload: 'payload',
  rejectReason: 'rejectReason',
  createdAt: 'createdAt',
  resolvedAt: 'resolvedAt'
};

exports.Prisma.OpsMissionScalarFieldEnum = {
  id: 'id',
  proposalId: 'proposalId',
  status: 'status',
  createdAt: 'createdAt',
  completedAt: 'completedAt'
};

exports.Prisma.OpsMissionStepScalarFieldEnum = {
  id: 'id',
  missionId: 'missionId',
  stepKind: 'stepKind',
  stepOrder: 'stepOrder',
  status: 'status',
  input: 'input',
  output: 'output',
  lastError: 'lastError',
  reservedAt: 'reservedAt',
  completedAt: 'completedAt',
  createdAt: 'createdAt'
};

exports.Prisma.OpsEventScalarFieldEnum = {
  id: 'id',
  source: 'source',
  kind: 'kind',
  tags: 'tags',
  payload: 'payload',
  missionId: 'missionId',
  createdAt: 'createdAt'
};

exports.Prisma.OpsPolicyScalarFieldEnum = {
  key: 'key',
  value: 'value',
  updatedAt: 'updatedAt'
};

exports.Prisma.OpsTriggerRuleScalarFieldEnum = {
  id: 'id',
  name: 'name',
  eventKind: 'eventKind',
  condition: 'condition',
  proposalTemplate: 'proposalTemplate',
  cooldownMin: 'cooldownMin',
  enabled: 'enabled',
  lastFiredAt: 'lastFiredAt',
  createdAt: 'createdAt'
};

exports.Prisma.OpsReactionScalarFieldEnum = {
  id: 'id',
  eventId: 'eventId',
  targetSkill: 'targetSkill',
  actionType: 'actionType',
  status: 'status',
  createdAt: 'createdAt',
  processedAt: 'processedAt'
};

exports.Prisma.Newsletter_subscribersScalarFieldEnum = {
  id: 'id',
  email: 'email',
  locale: 'locale',
  deviceId: 'deviceId',
  optInAt: 'optInAt',
  optedOutAt: 'optedOutAt',
  lastSentAt: 'lastSentAt'
};

exports.Prisma.Feedback_logScalarFieldEnum = {
  id: 'id',
  text: 'text',
  locale: 'locale',
  appUserId: 'appUserId',
  appVersion: 'appVersion',
  createdAt: 'createdAt'
};

exports.Prisma.Failed_resend_callsScalarFieldEnum = {
  id: 'id',
  callType: 'callType',
  payloadJson: 'payloadJson',
  error: 'error',
  attemptedAt: 'attemptedAt'
};

exports.Prisma.SortOrder = {
  asc: 'asc',
  desc: 'desc'
};

exports.Prisma.JsonNullValueInput = {
  JsonNull: Prisma.JsonNull
};

exports.Prisma.NullableJsonNullValueInput = {
  DbNull: Prisma.DbNull,
  JsonNull: Prisma.JsonNull
};

exports.Prisma.QueryMode = {
  default: 'default',
  insensitive: 'insensitive'
};

exports.Prisma.JsonNullValueFilter = {
  DbNull: Prisma.DbNull,
  JsonNull: Prisma.JsonNull,
  AnyNull: Prisma.AnyNull
};

exports.Prisma.NullsOrder = {
  first: 'first',
  last: 'last'
};


exports.Prisma.ModelName = {
  Token: 'Token',
  RefreshToken: 'RefreshToken',
  MobileProfile: 'MobileProfile',
  UserSubscription: 'UserSubscription',
  SubscriptionEvent: 'SubscriptionEvent',
  MonthlyVcGrant: 'MonthlyVcGrant',
  Profile: 'Profile',
  UserSetting: 'UserSetting',
  PushToken: 'PushToken',
  NudgeDelivery: 'NudgeDelivery',
  NudgeDeliverySend: 'NudgeDeliverySend',
  UserTrait: 'UserTrait',
  NudgeEvent: 'NudgeEvent',
  NudgeOutcome: 'NudgeOutcome',
  FeelingSession: 'FeelingSession',
  BanditModel: 'BanditModel',
  UserTypeEstimate: 'UserTypeEstimate',
  TypeStats: 'TypeStats',
  HookCandidate: 'HookCandidate',
  TiktokPost: 'TiktokPost',
  WisdomPattern: 'WisdomPattern',
  XPost: 'XPost',
  NotificationSchedule: 'NotificationSchedule',
  AgentPost: 'AgentPost',
  AgentAuditLog: 'AgentAuditLog',
  MemoryItem: 'MemoryItem',
  Initiative: 'Initiative',
  ResearchItem: 'ResearchItem',
  OpsProposal: 'OpsProposal',
  OpsMission: 'OpsMission',
  OpsMissionStep: 'OpsMissionStep',
  OpsEvent: 'OpsEvent',
  OpsPolicy: 'OpsPolicy',
  OpsTriggerRule: 'OpsTriggerRule',
  OpsReaction: 'OpsReaction',
  newsletter_subscribers: 'newsletter_subscribers',
  feedback_log: 'feedback_log',
  failed_resend_calls: 'failed_resend_calls'
};

/**
 * This is a stub Prisma Client that will error at runtime if called.
 */
class PrismaClient {
  constructor() {
    return new Proxy(this, {
      get(target, prop) {
        let message
        const runtime = getRuntime()
        if (runtime.isEdge) {
          message = `PrismaClient is not configured to run in ${runtime.prettyName}. In order to run Prisma Client on edge runtime, either:
- Use Prisma Accelerate: https://pris.ly/d/accelerate
- Use Driver Adapters: https://pris.ly/d/driver-adapters
`;
        } else {
          message = 'PrismaClient is unable to run in this browser environment, or has been bundled for the browser (running in `' + runtime.prettyName + '`).'
        }
        
        message += `
If this is unexpected, please open an issue: https://pris.ly/prisma-prisma-bug-report`

        throw new Error(message)
      }
    })
  }
}

exports.PrismaClient = PrismaClient

Object.assign(exports, Prisma)
