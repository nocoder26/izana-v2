export const en = {
  common: {
    loading: 'Loading...',
    error: 'Something went wrong',
    retry: "Let's try that again",
    done: 'Done \u2713',
    notNow: 'Not now',
    gotIt: 'Got it',
    continue: 'Continue \u2192',
    skipForNow: 'Skip for now',
  },
  landing: {
    headline:
      'Your fertility journey is unique. Your support should be too.',
    cta: 'Start my journey \u2014 free & anonymous',
    login: 'Already have an account? Log in',
    tagline: 'Personalised fertility wellness, powered by AI',
    privacy: 'Your data stays private. Always.',
    features: {
      personalised: 'A plan built just for you',
      evidence: 'Evidence-based guidance',
      support: '24/7 compassionate support',
    },
  },
  chat: {
    placeholder: 'Ask anything...',
    placeholderGrief: "I'm here whenever you're ready...",
    send: 'Send',
    stopGenerating: 'Stop generating',
    searchStages: {
      thinking: 'Thinking...',
      searching: 'Searching medical literature...',
      analysing: 'Analysing sources...',
      composing: 'Composing response...',
    },
    sources: 'Sources',
    followUp: 'Follow-up questions',
    todayHeader: 'Today',
    greeting: 'Good morning! How are you feeling today?',
  },
  onboarding: {
    welcome: 'Welcome to Izana',
    step1Title: 'Tell us about your journey',
    step1Subtitle: 'This helps us personalise your experience',
    step2Title: 'Your wellness goals',
    step2Subtitle: 'What matters most to you right now?',
    step3Title: 'Choose your identity',
    step3Subtitle: 'Pick a pseudonym and avatar \u2014 stay as private as you like',
    complete: 'All set! Your journey begins now.',
  },
  errors: {
    network: 'I lost my connection for a moment. Trying again...',
    server: 'Something unexpected happened on my end.',
    rateLimit:
      'I need a moment to catch up. Try again in a few seconds.',
    fileTooLarge:
      'That file is a bit large for me. Could you try one under 5MB?',
    invalidFile:
      'I can read PDFs and images (JPEG, PNG). Could you try one of those?',
    sessionExpired: "Your session has ended. Let\u2019s get you back in.",
    offline: 'This needs an internet connection.',
    planNotReady: 'Your plan is still being reviewed.',
  },
  toast: {
    mealDone: 'Breakfast logged \u2713 +10 points',
    exerciseDone: 'Yoga complete! 20 min \u2713',
    meditationDone: '10 minutes of calm. Beautiful. \u2713',
    checkinDone: 'Check-in done \u2014 thank you \u2713',
    streak7: '7-day streak! \uD83D\uDD25',
    planApproved: 'Your personalised plan has arrived! \uD83C\uDF89',
    copied: 'Copied \u2713',
    offlineQueued: 'Saved \u2014 will sync when connected',
    syncComplete: 'All caught up \u2713',
  },
  partner: {
    invite: 'Invite your partner',
    inviteDescription:
      'Share your journey with someone who cares.',
    generateCode: 'Generate invite code',
    codeExpires: 'Code expires in {days} days',
    supporting: 'Supporting {name}',
    sendEncouragement: 'Send encouragement',
    couplesMeditation: 'Couples meditation',
    askAboutSupporting: 'Ask about supporting',
    visibility: 'Partner visibility',
    visibilityDescription:
      'Control what your partner can see about your journey.',
    neverShared: 'Never shared',
  },
  sharing: {
    shareWithDoctor: 'Share with your doctor',
    selectContent: 'Select what to include in your report.',
    treatmentTimeline: 'Treatment timeline',
    bloodworkResults: 'Bloodwork results',
    checkinHistory: 'Check-in history',
    planAdherence: 'Plan adherence',
    wellnessProfile: 'Wellness profile',
    validFor: 'Valid for',
    maxViews: 'Max views',
    generateReport: 'Generate report',
    reportGenerated: 'Report generated',
    copyLink: 'Copy link',
  },
  offline: {
    banner: "You're offline \u2014 some features may be limited",
    reconnecting: 'Reconnecting...',
    caughtUp: 'All caught up \u2713',
    queued: '{count} queued action',
    queuedPlural: '{count} queued actions',
    syncing: 'Syncing...',
  },
} as const;

// Decision 18: Type-safe i18n — structure is enforced, but values are widened to string
// so translations can have different text while keeping the same keys.
type DeepStringify<T> = {
  [K in keyof T]: T[K] extends string ? string : DeepStringify<T[K]>;
};

export type TranslationKeys = DeepStringify<typeof en>;
