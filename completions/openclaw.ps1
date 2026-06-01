
Register-ArgumentCompleter -Native -CommandName openclaw -ScriptBlock {
    param($wordToComplete, $commandAst, $cursorPosition)
    
    $commandElements = $commandAst.CommandElements
    $commandPath = ""
    
    # Reconstruct command path (simple approximation)
    # Skip the executable name
    for ($i = 1; $i -lt $commandElements.Count; $i++) {
        $element = $commandElements[$i].Extent.Text
        if ($element -like "-*") { break }
        if ($i -eq $commandElements.Count - 1 -and $wordToComplete -ne "") { break } # Don't include current word being typed
        $commandPath += "$element "
    }
    $commandPath = $commandPath.Trim()
    
    # Root command
    if ($commandPath -eq "") {
         $completions = @('mcp','completion','setup','onboard','configure','config','backup','doctor','dashboard','reset','uninstall','message','memory','agent','agents','status','health','sessions','browser','acp','gateway','daemon','logs','system','models','approvals','nodes','devices','node','sandbox','tui','cron','dns','docs','hooks','webhooks','qr','clawbot','pairing','plugins','channels','directory','security','secrets','skills','update', '-V,','--container','--dev','--profile','--log-level','--no-color') 
         $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
            [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
         }
    }
    
    
            if ($commandPath -eq 'completion') {
                $completions = @('-s','-i','--write-state','-y')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'setup') {
                $completions = @('--workspace','--wizard','--non-interactive','--mode','--remote-url','--remote-token')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'onboard') {
                $completions = @('--workspace','--reset','--reset-scope','--non-interactive','--accept-risk','--flow','--mode','--auth-choice','--token-provider','--token','--token-profile-id','--token-expires-in','--secret-input-mode','--cloudflare-ai-gateway-account-id','--cloudflare-ai-gateway-gateway-id','--litellm-api-key','--anthropic-api-key','--byteplus-api-key','--chutes-api-key','--cloudflare-ai-gateway-api-key','--deepseek-api-key','--fal-api-key','--gemini-api-key','--huggingface-api-key','--kilocode-api-key','--kimi-code-api-key','--minimax-api-key','--mistral-api-key','--modelstudio-standard-api-key-cn','--modelstudio-standard-api-key','--modelstudio-api-key-cn','--modelstudio-api-key','--moonshot-api-key','--openai-api-key','--opencode-zen-api-key','--opencode-go-api-key','--openrouter-api-key','--qianfan-api-key','--synthetic-api-key','--together-api-key','--venice-api-key','--ai-gateway-api-key','--volcengine-api-key','--xai-api-key','--xiaomi-api-key','--zai-api-key','--custom-base-url','--custom-api-key','--custom-model-id','--custom-provider-id','--custom-compatibility','--gateway-port','--gateway-bind','--gateway-auth','--gateway-token','--gateway-token-ref-env','--gateway-password','--remote-url','--remote-token','--tailscale','--tailscale-reset-on-exit','--install-daemon','--no-install-daemon','--skip-daemon','--daemon-runtime','--skip-channels','--skip-skills','--skip-search','--skip-health','--skip-ui','--node-manager','--json')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'configure') {
                $completions = @('--section')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'config') {
                $completions = @('get','set','unset','file','validate','--section')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'config get') {
                $completions = @('--json')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'config set') {
                $completions = @('--strict-json','--json','--dry-run','--allow-exec','--ref-provider','--ref-source','--ref-id','--provider-source','--provider-allowlist','--provider-path','--provider-mode','--provider-timeout-ms','--provider-max-bytes','--provider-command','--provider-arg','--provider-no-output-timeout-ms','--provider-max-output-bytes','--provider-json-only','--provider-env','--provider-pass-env','--provider-trusted-dir','--provider-allow-insecure-path','--provider-allow-symlink-command','--batch-json','--batch-file')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'config validate') {
                $completions = @('--json')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'backup') {
                $completions = @('create','verify')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'backup create') {
                $completions = @('--output','--json','--dry-run','--verify','--only-config','--no-include-workspace')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'backup verify') {
                $completions = @('--json')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'doctor') {
                $completions = @('--no-workspace-suggestions','--yes','--repair','--fix','--force','--non-interactive','--generate-gateway-token','--deep')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'dashboard') {
                $completions = @('--no-open')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'reset') {
                $completions = @('--scope','--yes','--non-interactive','--dry-run')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'uninstall') {
                $completions = @('--service','--state','--workspace','--app','--all','--yes','--non-interactive','--dry-run')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'message') {
                $completions = @('send','broadcast','poll','react','reactions','read','edit','delete','pin','unpin','pins','permissions','search','thread','emoji','sticker','role','channel','member','voice','event','timeout','kick','ban')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'message send') {
                $completions = @('-m','-t','--media','--interactive','--buttons','--components','--card','--reply-to','--thread-id','--gif-playback','--force-document','--silent','--channel','--account','--json','--dry-run','--verbose')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'message broadcast') {
                $completions = @('--channel','--account','--json','--dry-run','--verbose','--targets','--message','--media')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'message poll') {
                $completions = @('-t','--channel','--account','--json','--dry-run','--verbose','--poll-question','--poll-option','--poll-multi','--poll-duration-hours','--poll-duration-seconds','--poll-anonymous','--poll-public','-m','--silent','--thread-id')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'message react') {
                $completions = @('-t','--channel','--account','--json','--dry-run','--verbose','--message-id','--emoji','--remove','--participant','--from-me','--target-author','--target-author-uuid')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'message reactions') {
                $completions = @('-t','--channel','--account','--json','--dry-run','--verbose','--message-id','--limit')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'message read') {
                $completions = @('-t','--channel','--account','--json','--dry-run','--verbose','--limit','--before','--after','--around','--include-thread')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'message edit') {
                $completions = @('--message-id','-m','-t','--channel','--account','--json','--dry-run','--verbose','--thread-id')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'message delete') {
                $completions = @('--message-id','-t','--channel','--account','--json','--dry-run','--verbose')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'message pin') {
                $completions = @('-t','--channel','--account','--json','--dry-run','--verbose','--message-id')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'message unpin') {
                $completions = @('-t','--channel','--account','--json','--dry-run','--verbose','--message-id')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'message pins') {
                $completions = @('-t','--channel','--account','--json','--dry-run','--verbose','--limit')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'message permissions') {
                $completions = @('-t','--channel','--account','--json','--dry-run','--verbose')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'message search') {
                $completions = @('--channel','--account','--json','--dry-run','--verbose','--guild-id','--query','--channel-id','--channel-ids','--author-id','--author-ids','--limit')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'message thread') {
                $completions = @('create','list','reply')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'message thread create') {
                $completions = @('--thread-name','-t','--channel','--account','--json','--dry-run','--verbose','--message-id','-m','--auto-archive-min')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'message thread list') {
                $completions = @('--guild-id','--channel','--account','--json','--dry-run','--verbose','--channel-id','--include-archived','--before','--limit')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'message thread reply') {
                $completions = @('-m','-t','--channel','--account','--json','--dry-run','--verbose','--media','--reply-to')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'message emoji') {
                $completions = @('list','upload')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'message emoji list') {
                $completions = @('--channel','--account','--json','--dry-run','--verbose','--guild-id')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'message emoji upload') {
                $completions = @('--guild-id','--channel','--account','--json','--dry-run','--verbose','--emoji-name','--media','--role-ids')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'message sticker') {
                $completions = @('send','upload')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'message sticker send') {
                $completions = @('-t','--channel','--account','--json','--dry-run','--verbose','--sticker-id','-m')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'message sticker upload') {
                $completions = @('--guild-id','--channel','--account','--json','--dry-run','--verbose','--sticker-name','--sticker-desc','--sticker-tags','--media')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'message role') {
                $completions = @('info','add','remove')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'message role info') {
                $completions = @('--guild-id','--channel','--account','--json','--dry-run','--verbose')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'message role add') {
                $completions = @('--guild-id','--user-id','--role-id','--channel','--account','--json','--dry-run','--verbose')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'message role remove') {
                $completions = @('--guild-id','--user-id','--role-id','--channel','--account','--json','--dry-run','--verbose')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'message channel') {
                $completions = @('info','list')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'message channel info') {
                $completions = @('-t','--channel','--account','--json','--dry-run','--verbose')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'message channel list') {
                $completions = @('--guild-id','--channel','--account','--json','--dry-run','--verbose')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'message member') {
                $completions = @('info')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'message member info') {
                $completions = @('--user-id','--channel','--account','--json','--dry-run','--verbose','--guild-id')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'message voice') {
                $completions = @('status')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'message voice status') {
                $completions = @('--guild-id','--user-id','--channel','--account','--json','--dry-run','--verbose')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'message event') {
                $completions = @('list','create')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'message event list') {
                $completions = @('--guild-id','--channel','--account','--json','--dry-run','--verbose')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'message event create') {
                $completions = @('--guild-id','--event-name','--start-time','--channel','--account','--json','--dry-run','--verbose','--end-time','--desc','--channel-id','--location','--event-type')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'message timeout') {
                $completions = @('--guild-id','--user-id','--channel','--account','--json','--dry-run','--verbose','--duration-min','--until','--reason')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'message kick') {
                $completions = @('--guild-id','--user-id','--channel','--account','--json','--dry-run','--verbose','--reason')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'message ban') {
                $completions = @('--guild-id','--user-id','--channel','--account','--json','--dry-run','--verbose','--reason','--delete-days')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'memory') {
                $completions = @('status','index','search')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'memory status') {
                $completions = @('--agent','--json','--deep','--index','--verbose')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'memory index') {
                $completions = @('--agent','--force','--verbose')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'memory search') {
                $completions = @('--query','--agent','--max-results','--min-score','--json')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'agent') {
                $completions = @('-m','-t','--session-id','--agent','--thinking','--verbose','--channel','--reply-to','--reply-channel','--reply-account','--local','--deliver','--json','--timeout')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'agents') {
                $completions = @('list','bindings','bind','unbind','add','set-identity','delete')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'agents list') {
                $completions = @('--json','--bindings')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'agents bindings') {
                $completions = @('--agent','--json')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'agents bind') {
                $completions = @('--agent','--bind','--json')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'agents unbind') {
                $completions = @('--agent','--bind','--all','--json')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'agents add') {
                $completions = @('--workspace','--model','--agent-dir','--bind','--non-interactive','--json')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'agents set-identity') {
                $completions = @('--agent','--workspace','--identity-file','--from-identity','--name','--theme','--emoji','--avatar','--json')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'agents delete') {
                $completions = @('--force','--json')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'status') {
                $completions = @('--json','--all','--usage','--deep','--timeout','--verbose','--debug')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'health') {
                $completions = @('--json','--timeout','--verbose','--debug')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'sessions') {
                $completions = @('cleanup','--json','--verbose','--store','--agent','--all-agents','--active')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'sessions cleanup') {
                $completions = @('--store','--agent','--all-agents','--dry-run','--enforce','--fix-missing','--active-key','--json')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'browser') {
                $completions = @('status','start','stop','reset-profile','tabs','tab','open','focus','close','profiles','create-profile','delete-profile','screenshot','snapshot','navigate','resize','click','type','press','hover','scrollintoview','drag','select','upload','waitfordownload','download','dialog','fill','wait','evaluate','console','pdf','responsebody','highlight','errors','requests','trace','cookies','storage','set','--browser-profile','--json','--url','--token','--timeout','--expect-final')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'browser tab') {
                $completions = @('new','select','close')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'browser create-profile') {
                $completions = @('--name','--color','--cdp-url','--user-data-dir','--driver')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'browser delete-profile') {
                $completions = @('--name')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'browser screenshot') {
                $completions = @('--full-page','--ref','--element','--type')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'browser snapshot') {
                $completions = @('--format','--target-id','--limit','--mode','--efficient','--interactive','--compact','--depth','--selector','--frame','--labels','--out')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'browser navigate') {
                $completions = @('--target-id')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'browser resize') {
                $completions = @('--target-id')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'browser click') {
                $completions = @('--target-id','--double','--button','--modifiers')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'browser type') {
                $completions = @('--submit','--slowly','--target-id')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'browser press') {
                $completions = @('--target-id')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'browser hover') {
                $completions = @('--target-id')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'browser scrollintoview') {
                $completions = @('--target-id','--timeout-ms')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'browser drag') {
                $completions = @('--target-id')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'browser select') {
                $completions = @('--target-id')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'browser upload') {
                $completions = @('--ref','--input-ref','--element','--target-id','--timeout-ms')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'browser waitfordownload') {
                $completions = @('--target-id','--timeout-ms')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'browser download') {
                $completions = @('--target-id','--timeout-ms')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'browser dialog') {
                $completions = @('--accept','--dismiss','--prompt','--target-id','--timeout-ms')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'browser fill') {
                $completions = @('--fields','--fields-file','--target-id')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'browser wait') {
                $completions = @('--time','--text','--text-gone','--url','--load','--fn','--timeout-ms','--target-id')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'browser evaluate') {
                $completions = @('--fn','--ref','--target-id')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'browser console') {
                $completions = @('--level','--target-id')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'browser pdf') {
                $completions = @('--target-id')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'browser responsebody') {
                $completions = @('--target-id','--timeout-ms','--max-chars')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'browser highlight') {
                $completions = @('--target-id')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'browser errors') {
                $completions = @('--clear','--target-id')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'browser requests') {
                $completions = @('--filter','--clear','--target-id')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'browser trace') {
                $completions = @('start','stop')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'browser trace start') {
                $completions = @('--target-id','--no-screenshots','--no-snapshots','--sources')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'browser trace stop') {
                $completions = @('--out','--target-id')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'browser cookies') {
                $completions = @('set','clear','--target-id')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'browser cookies set') {
                $completions = @('--url','--target-id')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'browser cookies clear') {
                $completions = @('--target-id')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'browser storage') {
                $completions = @('local','session')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'browser storage local') {
                $completions = @('get','set','clear')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'browser storage local get') {
                $completions = @('--target-id')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'browser storage local set') {
                $completions = @('--target-id')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'browser storage local clear') {
                $completions = @('--target-id')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'browser storage session') {
                $completions = @('get','set','clear')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'browser storage session get') {
                $completions = @('--target-id')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'browser storage session set') {
                $completions = @('--target-id')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'browser storage session clear') {
                $completions = @('--target-id')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'browser set') {
                $completions = @('viewport','offline','headers','credentials','geo','media','timezone','locale','device')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'browser set viewport') {
                $completions = @('--target-id')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'browser set offline') {
                $completions = @('--target-id')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'browser set headers') {
                $completions = @('--headers-json','--target-id')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'browser set credentials') {
                $completions = @('--clear','--target-id')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'browser set geo') {
                $completions = @('--clear','--accuracy','--origin','--target-id')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'browser set media') {
                $completions = @('--target-id')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'browser set timezone') {
                $completions = @('--target-id')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'browser set locale') {
                $completions = @('--target-id')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'browser set device') {
                $completions = @('--target-id')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'acp') {
                $completions = @('client','--url','--token','--token-file','--password','--password-file','--session','--session-label','--require-existing','--reset-session','--no-prefix-cwd','--provenance','-v')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'acp client') {
                $completions = @('--cwd','--server','--server-args','--server-verbose','-v')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'gateway') {
                $completions = @('run','status','install','uninstall','start','stop','restart','call','usage-cost','health','probe','discover','--port','--bind','--token','--auth','--password','--password-file','--tailscale','--tailscale-reset-on-exit','--allow-unconfigured','--dev','--reset','--force','--verbose','--claude-cli-logs','--ws-log','--compact','--raw-stream','--raw-stream-path')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'gateway run') {
                $completions = @('--port','--bind','--token','--auth','--password','--password-file','--tailscale','--tailscale-reset-on-exit','--allow-unconfigured','--dev','--reset','--force','--verbose','--claude-cli-logs','--ws-log','--compact','--raw-stream','--raw-stream-path')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'gateway status') {
                $completions = @('--url','--token','--password','--timeout','--no-probe','--require-rpc','--deep','--json')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'gateway install') {
                $completions = @('--port','--runtime','--token','--force','--json')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'gateway uninstall') {
                $completions = @('--json')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'gateway start') {
                $completions = @('--json')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'gateway stop') {
                $completions = @('--json')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'gateway restart') {
                $completions = @('--json')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'gateway call') {
                $completions = @('--params','--url','--token','--password','--timeout','--expect-final','--json')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'gateway usage-cost') {
                $completions = @('--days','--url','--token','--password','--timeout','--expect-final','--json')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'gateway health') {
                $completions = @('--url','--token','--password','--timeout','--expect-final','--json')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'gateway probe') {
                $completions = @('--url','--ssh','--ssh-identity','--ssh-auto','--token','--password','--timeout','--json')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'gateway discover') {
                $completions = @('--timeout','--json')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'daemon') {
                $completions = @('status','install','uninstall','start','stop','restart')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'daemon status') {
                $completions = @('--url','--token','--password','--timeout','--no-probe','--require-rpc','--deep','--json')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'daemon install') {
                $completions = @('--port','--runtime','--token','--force','--json')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'daemon uninstall') {
                $completions = @('--json')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'daemon start') {
                $completions = @('--json')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'daemon stop') {
                $completions = @('--json')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'daemon restart') {
                $completions = @('--json')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'logs') {
                $completions = @('--limit','--max-bytes','--follow','--interval','--json','--plain','--no-color','--local-time','--url','--token','--timeout','--expect-final')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'system') {
                $completions = @('event','heartbeat','presence')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'system event') {
                $completions = @('--text','--mode','--json','--url','--token','--timeout','--expect-final')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'system heartbeat') {
                $completions = @('last','enable','disable')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'system heartbeat last') {
                $completions = @('--json','--url','--token','--timeout','--expect-final')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'system heartbeat enable') {
                $completions = @('--json','--url','--token','--timeout','--expect-final')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'system heartbeat disable') {
                $completions = @('--json','--url','--token','--timeout','--expect-final')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'system presence') {
                $completions = @('--json','--url','--token','--timeout','--expect-final')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'models') {
                $completions = @('list','status','set','set-image','aliases','fallbacks','image-fallbacks','scan','auth','--status-json','--status-plain','--agent')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'models list') {
                $completions = @('--all','--local','--provider','--json','--plain')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'models status') {
                $completions = @('--json','--plain','--check','--probe','--probe-provider','--probe-profile','--probe-timeout','--probe-concurrency','--probe-max-tokens','--agent')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'models aliases') {
                $completions = @('list','add','remove')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'models aliases list') {
                $completions = @('--json','--plain')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'models fallbacks') {
                $completions = @('list','add','remove','clear')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'models fallbacks list') {
                $completions = @('--json','--plain')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'models image-fallbacks') {
                $completions = @('list','add','remove','clear')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'models image-fallbacks list') {
                $completions = @('--json','--plain')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'models scan') {
                $completions = @('--min-params','--max-age-days','--provider','--max-candidates','--timeout','--concurrency','--no-probe','--yes','--no-input','--set-default','--set-image','--json')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'models auth') {
                $completions = @('add','login','setup-token','paste-token','login-github-copilot','order','--agent')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'models auth login') {
                $completions = @('--provider','--method','--set-default')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'models auth setup-token') {
                $completions = @('--provider','--yes')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'models auth paste-token') {
                $completions = @('--provider','--profile-id','--expires-in')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'models auth login-github-copilot') {
                $completions = @('--yes')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'models auth order') {
                $completions = @('get','set','clear')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'models auth order get') {
                $completions = @('--provider','--agent','--json')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'models auth order set') {
                $completions = @('--provider','--agent')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'models auth order clear') {
                $completions = @('--provider','--agent')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'approvals') {
                $completions = @('get','set','allowlist')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'approvals get') {
                $completions = @('--node','--gateway','--url','--token','--timeout','--json')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'approvals set') {
                $completions = @('--node','--gateway','--file','--stdin','--url','--token','--timeout','--json')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'approvals allowlist') {
                $completions = @('add','remove')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'approvals allowlist add') {
                $completions = @('--node','--gateway','--agent','--url','--token','--timeout','--json')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'approvals allowlist remove') {
                $completions = @('--node','--gateway','--agent','--url','--token','--timeout','--json')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'nodes') {
                $completions = @('status','describe','list','pending','approve','reject','rename','invoke','run','notify','push','canvas','camera','screen','location')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'nodes status') {
                $completions = @('--connected','--last-connected','--url','--token','--timeout','--json')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'nodes describe') {
                $completions = @('--node','--url','--token','--timeout','--json')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'nodes list') {
                $completions = @('--connected','--last-connected','--url','--token','--timeout','--json')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'nodes pending') {
                $completions = @('--url','--token','--timeout','--json')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'nodes approve') {
                $completions = @('--url','--token','--timeout','--json')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'nodes reject') {
                $completions = @('--url','--token','--timeout','--json')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'nodes rename') {
                $completions = @('--node','--name','--url','--token','--timeout','--json')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'nodes invoke') {
                $completions = @('--node','--command','--params','--invoke-timeout','--idempotency-key','--url','--token','--timeout','--json')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'nodes run') {
                $completions = @('--node','--cwd','--env','--raw','--agent','--ask','--security','--command-timeout','--needs-screen-recording','--invoke-timeout','--url','--token','--timeout','--json')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'nodes notify') {
                $completions = @('--node','--title','--body','--sound','--priority','--delivery','--invoke-timeout','--url','--token','--timeout','--json')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'nodes push') {
                $completions = @('--node','--title','--body','--environment','--url','--token','--timeout','--json')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'nodes canvas') {
                $completions = @('snapshot','present','hide','navigate','eval','a2ui')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'nodes canvas snapshot') {
                $completions = @('--node','--format','--max-width','--quality','--invoke-timeout','--url','--token','--timeout','--json')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'nodes canvas present') {
                $completions = @('--node','--target','--x','--y','--width','--height','--invoke-timeout','--url','--token','--timeout','--json')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'nodes canvas hide') {
                $completions = @('--node','--invoke-timeout','--url','--token','--timeout','--json')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'nodes canvas navigate') {
                $completions = @('--node','--invoke-timeout','--url','--token','--timeout','--json')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'nodes canvas eval') {
                $completions = @('--js','--node','--invoke-timeout','--url','--token','--timeout','--json')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'nodes canvas a2ui') {
                $completions = @('push','reset')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'nodes canvas a2ui push') {
                $completions = @('--jsonl','--text','--node','--invoke-timeout','--url','--token','--timeout','--json')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'nodes canvas a2ui reset') {
                $completions = @('--node','--invoke-timeout','--url','--token','--timeout','--json')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'nodes camera') {
                $completions = @('list','snap','clip')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'nodes camera list') {
                $completions = @('--node','--url','--token','--timeout','--json')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'nodes camera snap') {
                $completions = @('--node','--facing','--device-id','--max-width','--quality','--delay-ms','--invoke-timeout','--url','--token','--timeout','--json')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'nodes camera clip') {
                $completions = @('--node','--facing','--device-id','--duration','--no-audio','--invoke-timeout','--url','--token','--timeout','--json')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'nodes screen') {
                $completions = @('record')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'nodes screen record') {
                $completions = @('--node','--screen','--duration','--fps','--no-audio','--out','--invoke-timeout','--url','--token','--timeout','--json')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'nodes location') {
                $completions = @('get')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'nodes location get') {
                $completions = @('--node','--max-age','--accuracy','--location-timeout','--invoke-timeout','--url','--token','--timeout','--json')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'devices') {
                $completions = @('list','remove','clear','approve','reject','rotate','revoke')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'devices list') {
                $completions = @('--url','--token','--password','--timeout','--json')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'devices remove') {
                $completions = @('--url','--token','--password','--timeout','--json')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'devices clear') {
                $completions = @('--pending','--yes','--url','--token','--password','--timeout','--json')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'devices approve') {
                $completions = @('--latest','--url','--token','--password','--timeout','--json')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'devices reject') {
                $completions = @('--url','--token','--password','--timeout','--json')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'devices rotate') {
                $completions = @('--device','--role','--scope','--url','--token','--password','--timeout','--json')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'devices revoke') {
                $completions = @('--device','--role','--url','--token','--password','--timeout','--json')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'node') {
                $completions = @('run','status','install','uninstall','stop','restart')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'node run') {
                $completions = @('--host','--port','--tls','--tls-fingerprint','--node-id','--display-name')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'node status') {
                $completions = @('--json')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'node install') {
                $completions = @('--host','--port','--tls','--tls-fingerprint','--node-id','--display-name','--runtime','--force','--json')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'node uninstall') {
                $completions = @('--json')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'node stop') {
                $completions = @('--json')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'node restart') {
                $completions = @('--json')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'sandbox') {
                $completions = @('list','recreate','explain')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'sandbox list') {
                $completions = @('--json','--browser')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'sandbox recreate') {
                $completions = @('--all','--session','--agent','--browser','--force')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'sandbox explain') {
                $completions = @('--session','--agent','--json')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'tui') {
                $completions = @('--url','--token','--password','--session','--deliver','--thinking','--message','--timeout-ms','--history-limit')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'cron') {
                $completions = @('status','list','add','rm','enable','disable','runs','run','edit')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'cron status') {
                $completions = @('--json','--url','--token','--timeout','--expect-final')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'cron list') {
                $completions = @('--all','--json','--url','--token','--timeout','--expect-final')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'cron add') {
                $completions = @('--name','--description','--disabled','--delete-after-run','--keep-after-run','--agent','--session','--session-key','--wake','--at','--every','--cron','--tz','--stagger','--exact','--system-event','--message','--thinking','--model','--timeout-seconds','--light-context','--announce','--deliver','--no-deliver','--channel','--to','--account','--best-effort-deliver','--json','--url','--token','--timeout','--expect-final')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'cron rm') {
                $completions = @('--json','--url','--token','--timeout','--expect-final')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'cron enable') {
                $completions = @('--url','--token','--timeout','--expect-final')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'cron disable') {
                $completions = @('--url','--token','--timeout','--expect-final')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'cron runs') {
                $completions = @('--id','--limit','--url','--token','--timeout','--expect-final')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'cron run') {
                $completions = @('--due','--url','--token','--timeout','--expect-final')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'cron edit') {
                $completions = @('--name','--description','--enable','--disable','--delete-after-run','--keep-after-run','--session','--agent','--clear-agent','--session-key','--clear-session-key','--wake','--at','--every','--cron','--tz','--stagger','--exact','--system-event','--message','--thinking','--model','--timeout-seconds','--light-context','--no-light-context','--announce','--deliver','--no-deliver','--channel','--to','--account','--best-effort-deliver','--no-best-effort-deliver','--failure-alert','--no-failure-alert','--failure-alert-after','--failure-alert-channel','--failure-alert-to','--failure-alert-cooldown','--failure-alert-mode','--failure-alert-account-id','--url','--token','--timeout','--expect-final')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'dns') {
                $completions = @('setup')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'dns setup') {
                $completions = @('--domain','--apply')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'hooks') {
                $completions = @('list','info','check','enable','disable','install','update')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'hooks list') {
                $completions = @('--eligible','--json','-v')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'hooks info') {
                $completions = @('--json')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'hooks check') {
                $completions = @('--json')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'hooks install') {
                $completions = @('-l','--pin')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'hooks update') {
                $completions = @('--all','--dry-run')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'webhooks') {
                $completions = @('gmail')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'webhooks gmail') {
                $completions = @('setup','run')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'webhooks gmail setup') {
                $completions = @('--account','--project','--topic','--subscription','--label','--hook-url','--hook-token','--push-token','--bind','--port','--path','--include-body','--max-bytes','--renew-minutes','--tailscale','--tailscale-path','--tailscale-target','--push-endpoint','--json')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'webhooks gmail run') {
                $completions = @('--account','--topic','--subscription','--label','--hook-url','--hook-token','--push-token','--bind','--port','--path','--include-body','--max-bytes','--renew-minutes','--tailscale','--tailscale-path','--tailscale-target')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'qr') {
                $completions = @('--remote','--url','--public-url','--token','--password','--setup-code-only','--no-ascii','--json')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'clawbot') {
                $completions = @('qr')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'clawbot qr') {
                $completions = @('--remote','--url','--public-url','--token','--password','--setup-code-only','--no-ascii','--json')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'pairing') {
                $completions = @('list','approve')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'pairing list') {
                $completions = @('--channel','--account','--json')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'pairing approve') {
                $completions = @('--channel','--account','--notify')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'plugins') {
                $completions = @('list','inspect','enable','disable','uninstall','install','update','doctor','marketplace')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'plugins list') {
                $completions = @('--json','--enabled','--verbose')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'plugins inspect') {
                $completions = @('--all','--json')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'plugins uninstall') {
                $completions = @('--keep-files','--keep-config','--force','--dry-run')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'plugins install') {
                $completions = @('-l','--pin','--marketplace')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'plugins update') {
                $completions = @('--all','--dry-run')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'plugins marketplace') {
                $completions = @('list')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'plugins marketplace list') {
                $completions = @('--json')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'channels') {
                $completions = @('list','status','capabilities','resolve','logs','add','remove','login','logout')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'channels list') {
                $completions = @('--no-usage','--json')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'channels status') {
                $completions = @('--probe','--timeout','--json')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'channels capabilities') {
                $completions = @('--channel','--account','--target','--timeout','--json')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'channels resolve') {
                $completions = @('--channel','--account','--kind','--json')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'channels logs') {
                $completions = @('--channel','--lines','--json')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'channels add') {
                $completions = @('--channel','--account','--name','--token','--private-key','--token-file','--bot-token','--app-token','--signal-number','--cli-path','--db-path','--service','--region','--auth-dir','--http-url','--http-host','--http-port','--webhook-path','--webhook-url','--audience-type','--audience','--homeserver','--user-id','--access-token','--password','--device-name','--initial-sync-limit','--ship','--url','--relay-urls','--code','--group-channels','--dm-allowlist','--auto-discover-channels','--no-auto-discover-channels','--use-env')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'channels remove') {
                $completions = @('--channel','--account','--delete')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'channels login') {
                $completions = @('--channel','--account','--verbose')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'channels logout') {
                $completions = @('--channel','--account')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'directory') {
                $completions = @('self','peers','groups')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'directory self') {
                $completions = @('--channel','--account','--json')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'directory peers') {
                $completions = @('list')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'directory peers list') {
                $completions = @('--channel','--account','--json','--query','--limit')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'directory groups') {
                $completions = @('list','members')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'directory groups list') {
                $completions = @('--channel','--account','--json','--query','--limit')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'directory groups members') {
                $completions = @('--group-id','--channel','--account','--json','--limit')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'security') {
                $completions = @('audit')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'security audit') {
                $completions = @('--deep','--token','--password','--fix','--json')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'secrets') {
                $completions = @('reload','audit','configure','apply')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'secrets reload') {
                $completions = @('--json','--url','--token','--timeout','--expect-final')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'secrets audit') {
                $completions = @('--check','--allow-exec','--json')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'secrets configure') {
                $completions = @('--apply','--yes','--providers-only','--skip-provider-setup','--agent','--allow-exec','--plan-out','--json')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'secrets apply') {
                $completions = @('--from','--dry-run','--allow-exec','--json')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'skills') {
                $completions = @('search','install','update','list','info','check')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'skills search') {
                $completions = @('--limit','--json')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'skills install') {
                $completions = @('--version','--force')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'skills update') {
                $completions = @('--all')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'skills list') {
                $completions = @('--json','--eligible','-v')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'skills info') {
                $completions = @('--json')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'skills check') {
                $completions = @('--json')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'update') {
                $completions = @('wizard','status','--json','--no-restart','--dry-run','--channel','--tag','--timeout','--yes')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'update wizard') {
                $completions = @('--timeout')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

            if ($commandPath -eq 'update status') {
                $completions = @('--json','--timeout')
                $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }

}
