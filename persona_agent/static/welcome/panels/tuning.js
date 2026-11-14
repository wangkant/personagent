"use strict";
PA.strings({
  en: {
    tuning_title: "Advanced settings",
    tuning_lead: "These settings are optional and all have defaults. Change only what you need.",
    tuning_sec_who: "Admin and access",
    tuning_sec_talk: "Speaking and reply style",
    tuning_sec_models: "Models",
    tuning_sec_learning: "Learning",
    tuning_sec_memory: "Memory",
    tuning_sec_more: "Other settings",
    tuning_more_note: "Each field shows the value currently set. An empty field uses its default, shown in grey. Times are in seconds.",
    tuning_save: "Save",
    tuning_saving: "Saving…",
    tuning_saved: "Saved.",
    tuning_saved_restarted: "Saved. The character has restarted with the new settings.",
    tuning_saved_later: "Saved. The changes take effect the next time the character starts.",
    tuning_saved_persona: "Saved. The character has restarted, and its persona now uses your name.",
    tuning_nothing: "There are no changes to save.",
    tuning_pick: "Choose from recent chats",
    tuning_picking: "Loading…",
    tuning_pick_none: "There are no chats yet. People who message the character on a connected platform will appear here.",
    tuning_pick_not_running: "The character is not running, so recent chats cannot be read. Sending a message under {chat} or connecting a platform under {platforms} starts it; then try again.",
    tuning_pick_off: "Activity data is turned off (under {more}), so recent chats cannot be listed.",
    tuning_people: "People who sent private messages",
    tuning_groups: "Groups",
    tuning_me: "This is me",
    tuning_not_me: "This is not me",
    tuning_may_dm: "Allow private messages",
    tuning_answer_here: "Reply in this group",
    tuning_restricted: "On {platforms}, the character replies only to the entries listed and ignores all others.",
    tuning_unrestricted: "Empty: no restriction.",
    tuning_tz_auto: "Automatic ({offset})",
    tuning_preset: "How often it starts conversations",
    tuning_preset_hint: "Applies only when “{feature}” is turned on above. A higher frequency uses more model calls.",
    tuning_preset_rarely: "Rarely (default)",
    tuning_preset_sometimes: "Occasionally",
    tuning_preset_often: "Frequently",
    tuning_preset_custom: "Custom (set under {more})",
    tuning_cooldowns: "At least {group} h between two conversations it starts in the same group, and at least {dm} h for the same person.",
    tuning_style: "Reply style",
    tuning_style_hint: "What replies may contain. By default: no emoji, no extra symbols, and at most 800 characters.",
    tuning_emoji: "Allow emoji",
    tuning_cs_ellipsis: "Ellipsis …",
    tuning_cs_music: "Music notes ♪",
    tuning_cs_arrows: "Arrows →",
    tuning_max_chars: "Maximum reply length (characters)",
    tuning_max_chars_hint: "From {min} to {max}. Longer replies are truncated.",
    tuning_fresh: "Restart learning",
    tuning_freshing: "Restarting learning…",
    tuning_fresh_hint: "What the character has learned will no longer be used, but it stays on this computer. Current learning label: {label}",
    tuning_fresh_none: "(none)",
    tuning_fresh_ask: "Restart learning? What the character has learned so far will no longer be used. Nothing is deleted; to use it again, enter the previous label under {more}.",
    tuning_fresh_yes: "Restart learning",
    tuning_fresh_done: "Learning has restarted. The previous label was {old}.",
    tuning_ask_off: "Turn off replies? The character keeps running but does not reply to any message until you turn replies on again.",
    tuning_ask_off_yes: "Turn off replies",
    tuning_rename_note: "A new name creates a new character. What the current character has learned stays on this computer but is no longer used.",
    tuning_rename_ask: "Rename {old} to {new}? A new name creates a new character. What {old} has learned stays on this computer but is no longer used.",
    tuning_rename_yes: "Rename",
    tuning_key_saved: "Saved ({hint}). Leave empty to keep it.",
    tuning_err_invalid: "{field}: the value is not valid. Correct it and save again.",
    tuning_err_range: "{field}: enter a number from {min} to {max}, or leave the field empty.",
    tuning_err_ids: "{field}: enter ids as platform:id, separated by commas, for example telegram:12345.",
    tuning_err_card: "Maximum reply length: enter a number from {min} to {max}, or leave the field empty.",
    tuning_key_needed: "The backup model is on a different model service and needs its own key. Enter the key for that service.",
    tuning_https: "The backup model's service address must start with https:// (http:// is accepted only for this computer).",
    tuning_fallback_rejected: "The backup model's service rejected the key. Check the key and the service address.",
    tuning_fallback_limited: "The backup model's service is busy. Try saving again in a minute.",
    tuning_fallback_unreachable: "The backup model could not be reached. Check the model name and the service address.",
    tuning_card_broken: "The reply style file (persona.card.json) cannot be read. Correct or delete it, then save again.",
    tuning_card_outside: "The reply style file must be inside the personagent folder. Correct PERSONA_CARD_FILE in .env.",
    tuning_not_configured: "Connect a model at the top of this page first.",
    tuning_unknown: "This page is out of date. Close personagent and open it again.",
    tuning_f_admin_name: "Your name",
    tuning_h_admin_name: "The name the character uses for you, its admin.",
    tuning_f_admin_relationship: "Your relationship to the character",
    tuning_h_admin_relationship: "For example friend, older brother or manager. Leave empty if it should not be mentioned.",
    tuning_f_admin_ids: "Your accounts",
    tuning_h_admin_ids: "Your ids, as platform:id, separated by commas. The surest way: send the character one private message on that platform, then use “{pick}” below and select “{me}”. A number without a platform is read as a QQ number, which applies only to QQ through OneBot (NapCat); the QQ bot connected by scan does not see QQ numbers. The character treats these accounts as its admin: it is more familiar with you, your corrections alone are enough to teach it, and it forgets what it noted when you ask.",
    tuning_f_access_groups: "Reply only in these groups",
    tuning_h_access_groups: "Group ids, as platform:id, separated by commas, for example telegram:-1001234567890. The easiest way is “{pick}” above, once the character has received a message in that group. Once one group of a platform is listed, the character does not reply in any other group on that platform.",
    tuning_f_access_dm_users: "Others allowed to send private messages",
    tuning_h_access_dm_users: "You do not need to list yourself. Once one person of a platform is listed, no one else on that platform can message the character privately.",
    tuning_f_persona_tz_offset_hours: "Time zone",
    tuning_h_persona_tz_offset_hours: "Sets the character's clock and its quiet hours, 02:00 to 07:00 in this time zone, during which it neither starts conversations nor joins in unprompted.",
    tuning_f_chat_trigger_count: "Messages before joining in",
    tuning_h_chat_trigger_count: "How many messages others send in a group before the character considers joining in unprompted. A lower number makes it more active and uses more model calls.",
    tuning_f_llm_fallback_model: "Backup model",
    tuning_h_llm_fallback_model: "Used when the main model is busy, failing or rate-limited. Chat content is also sent to it. Empty: no backup model.",
    tuning_f_llm_fallback_base_url: "Backup model service address",
    tuning_h_llm_fallback_base_url: "Empty: the same model service as the main model. A different service needs its own key below.",
    tuning_f_llm_fallback_api_key: "Backup model key",
    tuning_h_llm_fallback_api_key: "Required only when the backup model is on a different model service.",
    tuning_f_llm_judge_model: "Model for quick decisions",
    tuning_h_llm_judge_model: "A low-cost model that only decides whether to speak when no one has addressed the character. Empty: the backup model, or the main model if there is no backup.",
    tuning_f_llm_dm_model: "Model for private chats",
    tuning_h_llm_dm_model: "Another model on the main model's service, used for one-to-one chats. Empty: the main model.",
    tuning_f_react_learn_enabled: "Learn from reactions",
    tuning_h_react_learn_enabled: "The character reads replies to its messages to learn which ones were well received. Each reading uses a small model call.",
    tuning_f_react_elicit_enabled: "Ask for clarification after a complaint",
    tuning_h_react_elicit_enabled: "When someone says a reply was wrong without saying why, the character may later ask once what was expected.",
    tuning_f_promote_auto_enabled: "Put learned items into use automatically",
    tuning_h_promote_auto_enabled: "Off: nothing new is put into use, neither through agreeing reactions nor by the character's own decisions. Items already in use remain in use.",
    tuning_f_promote_min_speakers: "Require agreement from a second person",
    tuning_h_promote_min_speakers: "An item is put into use only after reactions from two different people. Until then, the character continues to observe it.",
    tuning_f_promote_judge_enabled: "Let the character decide what reactions cannot settle",
    tuning_h_promote_judge_enabled: "When reactions disagree, two revisions compete, or an item has only approval behind it, the character decides by itself whether to use it, set it aside or keep observing it. Each decision uses one model call; an answer that cannot be used is requested once more. Off: such items remain under observation.",
    tuning_f_promote_observe_max_days: "Days under observation before an item is set aside",
    tuning_h_promote_observe_max_days: "An item that receives no new reaction for this many days is set aside. 0: never.",
    tuning_f_agent_enabled: "Reply to messages",
    tuning_h_agent_enabled: "Off: the character stays connected but does not reply to any message.",
    tuning_f_dashboard_enabled: "Keep activity data",
    tuning_h_dashboard_enabled: "Supplies the {activity} view: why the character spoke or stayed silent, and what it learned. Off: the {activity} view stays empty, and a chat can no longer be forgotten from the {chat} view or the {activity} view.",
    tuning_f_update_check_enabled: "Check for updates",
    tuning_h_update_check_enabled: "Once a day, pypi.org is asked whether a newer version is available. Only the version number is sent.",
    tuning_f_proactive_interval_s: "Interval between speak-first checks",
    tuning_h_proactive_interval_s: "How often the character checks whether to start a conversation.",
    tuning_f_proactive_min_silence_s: "Group silence before speaking first",
    tuning_h_proactive_min_silence_s: "A group must be silent for this long before the character starts a conversation.",
    tuning_f_proactive_cooldown_s: "Interval between conversations started in a group",
    tuning_h_proactive_cooldown_s: "The minimum time between two conversations the character starts in the same group.",
    tuning_f_proactive_prob: "Probability per check (groups)",
    tuning_h_proactive_prob: "From 0 to 1; 0.25 means about one check in four.",
    tuning_f_proactive_dm_min_silence_s: "Private chat silence before speaking first",
    tuning_h_proactive_dm_min_silence_s: "A private chat must be silent for this long before the character starts a conversation.",
    tuning_f_proactive_dm_cooldown_s: "Interval between conversations started in a private chat",
    tuning_h_proactive_dm_cooldown_s: "The minimum time between two private conversations the character starts with the same person.",
    tuning_f_proactive_dm_prob: "Probability per check (private chats)",
    tuning_h_proactive_dm_prob: "From 0 to 1.",
    tuning_f_chat_context_messages: "Recent messages kept per chat",
    tuning_h_chat_context_messages: "Messages kept for replies and for consolidation. A reply reads at most the last 60.",
    tuning_f_memory_calls_per_day: "Memory consolidation calls per day",
    tuning_h_memory_calls_per_day: "Model calls per day, for all chats together, that move conversation into long-term memory. Zero turns them off.",
    tuning_f_memory_tidy_every: "Notes that start a consolidation",
    tuning_h_memory_tidy_every: "When this many notes have been written in replies since a chat's last consolidation, that chat is consolidated. Zero turns off every memory model call.",
    tuning_f_memory_prompt_chars: "Remembered material per reply (characters)",
    tuning_h_memory_prompt_chars: "Characters of remembered material placed in each reply: the summary of earlier conversation, facts and events.",
    tuning_f_memory_episodes_max: "Events kept per chat",
    tuning_h_memory_episodes_max: "When a chat holds more events, the least useful are removed; they can be restored for 30 days.",
    tuning_f_memory_keep_recent: "Keep recent messages on this computer",
    tuning_h_memory_keep_recent: "The recent messages of each chat are kept on disk for 72 hours, so that a restart does not lose them. Off: they are kept only while the character runs.",
    tuning_f_chat_followup_window_s: "Follow-up window",
    tuning_h_chat_followup_window_s: "After the character replies, new messages within this time are treated as replies to it.",
    tuning_f_react_ttl_s: "Reaction window per reply",
    tuning_h_react_ttl_s: "After this time, reactions to that reply are no longer read.",
    tuning_f_react_max_pending: "Replies watched per chat",
    tuning_h_react_max_pending: "How many of its recent replies the character watches for reactions at the same time.",
    tuning_f_react_model: "Model for reading reactions",
    tuning_h_react_model: "Empty: the model for quick decisions.",
    tuning_f_react_fix_window_s: "Second-attempt window",
    tuning_h_react_fix_window_s: "After a reply is rejected, the character's next reply within this time counts as a second attempt.",
    tuning_f_react_elicit_delay_s: "Delay before asking for clarification",
    tuning_h_react_elicit_delay_s: "Prevents the question from immediately following the character's own reply.",
    tuning_f_react_elicit_cooldown_s: "Interval between clarification questions",
    tuning_h_react_elicit_cooldown_s: "Within one chat, prevents repeated questions.",
    tuning_f_promote_min_events: "Consistent reactions required",
    tuning_h_promote_min_events: "At least 2, so that a single misreading cannot cause a change.",
    tuning_f_promote_min_strong: "Explicit corrections among them",
    tuning_h_promote_min_strong: "At least 1: a correction that states what the reply should have been.",
    tuning_f_promote_evidence_max_age_days: "Maximum age of reactions (days)",
    tuning_h_promote_evidence_max_age_days: "Older reactions are not counted. 0: no limit.",
    tuning_f_promote_require_same_conversation: "Combine reactions only within one chat",
    tuning_h_promote_require_same_conversation: "Prevents a single person from changing the character's behaviour in every chat at once.",
    tuning_f_promote_max_examples: "Maximum learned examples",
    tuning_h_promote_max_examples: "0: no limit. More examples mean more material to search for every reply.",
    tuning_f_promote_max_feedback: "Maximum learned corrections",
    tuning_h_promote_max_feedback: "0: no limit. More corrections mean more material to search for every reply.",
    tuning_f_promote_judge_model: "Model for the character's own decisions",
    tuning_h_promote_judge_model: "Empty: the model for reading reactions.",
    tuning_f_promote_judge_interval_s: "Interval between the character's decision rounds",
    tuning_h_promote_judge_interval_s: "How often the character reviews the items that reactions cannot settle. At least 60.",
    tuning_f_promote_judge_batch: "Decisions per round",
    tuning_h_promote_judge_batch: "The greatest number of items the character decides in one round. Each decision uses one model call; an answer that cannot be used is requested once more.",
    tuning_f_persona_version: "Learning label",
    tuning_h_persona_version: "Persona edits under the same label count as the same character. A new label restarts learning; a previous label restores what was learned under it.",
  },
  zh: {
    tuning_title: "高级设置",
    tuning_lead: "以下设置均为可选项，且都有默认值。只需修改需要调整的项目。",
    tuning_sec_who: "管理员与回复范围",
    tuning_sec_talk: "发言与回复风格",
    tuning_sec_models: "模型",
    tuning_sec_learning: "学习",
    tuning_sec_memory: "记忆",
    tuning_sec_more: "其他设置",
    tuning_more_note: "各项显示当前设置的值；留空即使用灰色显示的默认值。时间单位均为秒。",
    tuning_save: "保存",
    tuning_saving: "正在保存…",
    tuning_saved: "已保存。",
    tuning_saved_restarted: "已保存，角色已按新设置重新启动。",
    tuning_saved_later: "已保存，将在角色下次启动时生效。",
    tuning_saved_persona: "已保存，角色已重新启动，人设中的称呼已同步更新。",
    tuning_nothing: "没有需要保存的更改。",
    tuning_pick: "从最近的聊天中选择",
    tuning_picking: "正在读取…",
    tuning_pick_none: "暂无聊天记录。有人在已连接的平台上向角色发送消息后，将显示在此处。",
    tuning_pick_not_running: "角色未在运行，无法读取最近的聊天。在「{chat}」中发送一条消息，或在「{platforms}」中连接一个平台，角色即会启动，届时请重试。",
    tuning_pick_off: "动态数据已关闭（位于「{more}」），无法列出最近的聊天。",
    tuning_people: "曾私聊角色的用户",
    tuning_groups: "群聊",
    tuning_me: "这是我",
    tuning_not_me: "这不是我",
    tuning_may_dm: "允许私聊",
    tuning_answer_here: "在此群聊中回复",
    tuning_restricted: "在 {platforms} 上，角色仅回复列出的对象，不回复其他对象。",
    tuning_unrestricted: "留空即不限制。",
    tuning_tz_auto: "自动（{offset}）",
    tuning_preset: "主动发起对话的频率",
    tuning_preset_hint: "仅在上方开启「{feature}」后生效。频率越高，调用模型的次数越多。",
    tuning_preset_rarely: "较少（默认）",
    tuning_preset_sometimes: "适中",
    tuning_preset_often: "较多",
    tuning_preset_custom: "自定义（在「{more}」中修改）",
    tuning_cooldowns: "同一群聊中两次主动发起对话至少间隔 {group} 小时；对同一用户至少间隔 {dm} 小时。",
    tuning_style: "回复风格",
    tuning_style_hint: "回复中允许使用的内容。默认不使用表情和特殊符号，长度不超过 800 字。",
    tuning_emoji: "允许使用表情",
    tuning_cs_ellipsis: "省略号 …",
    tuning_cs_music: "音符 ♪",
    tuning_cs_arrows: "箭头 →",
    tuning_max_chars: "单条回复最大长度（字）",
    tuning_max_chars_hint: "范围为 {min} 至 {max}，超出部分将被截断。",
    tuning_fresh: "重新开始学习",
    tuning_freshing: "正在重新开始学习…",
    tuning_fresh_hint: "角色此前学到的内容将不再使用，但仍保留在本机。当前学习标签：{label}",
    tuning_fresh_none: "（无）",
    tuning_fresh_ask: "确定重新开始学习吗？角色此前学到的内容将不再使用，但不会被删除。如需恢复，可在「{more}」中填回原标签。",
    tuning_fresh_yes: "重新开始学习",
    tuning_fresh_done: "已重新开始学习。原标签为 {old}。",
    tuning_ask_off: "确定关闭回复吗？角色将保持运行，但在你重新开启之前不回复任何消息。",
    tuning_ask_off_yes: "关闭回复",
    tuning_rename_note: "更改名字即创建一个新角色：当前角色学到的内容仍保留在本机，但不再使用。",
    tuning_rename_ask: "确定将 {old} 改名为 {new} 吗？更改名字即创建一个新角色：{old} 学到的内容仍保留在本机，但不再使用。",
    tuning_rename_yes: "改名",
    tuning_key_saved: "已保存（{hint}）。留空即保留原密钥。",
    tuning_err_invalid: "「{field}」的值无效，请修改后重新保存。",
    tuning_err_range: "「{field}」须为 {min} 至 {max} 之间的数字，或留空。",
    tuning_err_ids: "「{field}」须写成 平台:编号 的形式，以逗号分隔，例如 telegram:12345。",
    tuning_err_card: "「单条回复最大长度」须为 {min} 至 {max} 之间的数字，或留空。",
    tuning_key_needed: "备用模型位于另一模型服务，需要该服务的密钥。请填写该服务的密钥。",
    tuning_https: "备用模型的服务地址须以 https:// 开头（http:// 仅限本机地址）。",
    tuning_fallback_rejected: "备用模型的服务拒绝了该密钥，请检查密钥和服务地址。",
    tuning_fallback_limited: "备用模型的服务当前繁忙，请稍后重新保存。",
    tuning_fallback_unreachable: "无法连接备用模型，请检查模型名称和服务地址。",
    tuning_card_broken: "回复风格文件（persona.card.json）无法读取。请修正或删除该文件后重新保存。",
    tuning_card_outside: "回复风格文件必须位于 personagent 文件夹内。请修改 .env 中的 PERSONA_CARD_FILE。",
    tuning_not_configured: "请先在本页上方连接模型。",
    tuning_unknown: "此页面已过期，请关闭 personagent 后重新打开。",
    tuning_f_admin_name: "角色对你的称呼",
    tuning_h_admin_name: "角色以此名称称呼你，即它的管理员。",
    tuning_f_admin_relationship: "你与角色的关系",
    tuning_h_admin_relationship: "例如朋友、兄长、上司。留空则不提及。",
    tuning_f_admin_ids: "你的账号",
    tuning_h_admin_ids: "你在各平台上的编号，格式为 平台:编号，多个以逗号分隔。最稳妥的做法是：先在该平台上私聊角色一次，再点击下方的「{pick}」，选择「{me}」。不带平台的纯数字视为 QQ 号，仅适用于经 OneBot（NapCat）接入的 QQ；扫码接入的 QQ 机器人获取不到 QQ 号。角色将这些账号视为管理员：与你更为亲近，仅凭你的纠正即可学习，并会按你的要求忘记记下的内容。",
    tuning_f_access_groups: "仅在以下群聊中回复",
    tuning_h_access_groups: "填写群聊编号，格式为 平台:编号，多个以逗号分隔，例如 telegram:-1001234567890。角色在该群中收到过消息后，使用上方的「{pick}」最为简便。某个平台一旦填写了任一群聊，角色在该平台的其他群聊中将不再回复。",
    tuning_f_access_dm_users: "允许私聊的其他用户",
    tuning_h_access_dm_users: "无需填写你自己。某个平台一旦填写了任一用户，该平台的其他用户将无法私聊角色。",
    tuning_f_persona_tz_offset_hours: "角色所在时区",
    tuning_h_persona_tz_offset_hours: "决定角色使用的时间和休息时段：按此时区 02:00 至 07:00，角色既不主动发起对话，也不主动加入群聊讨论。",
    tuning_f_chat_trigger_count: "主动加入讨论前的消息数",
    tuning_h_chat_trigger_count: "群聊中其他人的消息达到此数量后，角色才会考虑主动加入讨论。数值越小，角色越活跃，调用模型的次数也越多。",
    tuning_f_llm_fallback_model: "备用模型",
    tuning_h_llm_fallback_model: "主模型繁忙、出错或被限流时改用此模型。聊天内容也会发送给该模型。留空即不使用备用模型。",
    tuning_f_llm_fallback_base_url: "备用模型服务地址",
    tuning_h_llm_fallback_base_url: "留空即与主模型使用同一模型服务。使用其他模型服务时，须在下方填写该服务的密钥。",
    tuning_f_llm_fallback_api_key: "备用模型密钥",
    tuning_h_llm_fallback_api_key: "仅当备用模型位于其他模型服务时需要填写。",
    tuning_f_llm_judge_model: "快速判断模型",
    tuning_h_llm_judge_model: "无人呼叫角色时，用于判断是否发言的低成本模型。留空则使用备用模型；未设置备用模型时使用主模型。",
    tuning_f_llm_dm_model: "私聊模型",
    tuning_h_llm_dm_model: "主模型所在模型服务上的另一个模型，专用于一对一私聊。留空即使用主模型。",
    tuning_f_react_learn_enabled: "从他人的反应中学习",
    tuning_h_react_learn_enabled: "角色读取他人对其消息的回应，以了解哪些回复效果较好。每次读取会额外调用一次模型。",
    tuning_f_react_elicit_enabled: "回复被否定后询问原因",
    tuning_h_react_elicit_enabled: "有人指出回复不当但未说明原因时，角色可能在稍后主动询问一次。",
    tuning_f_promote_auto_enabled: "自动将学到的内容投入使用",
    tuning_h_promote_auto_enabled: "关闭后，不会再有新的内容投入使用，无论是通过一致的反应还是角色的自行判断。已在使用的内容不受影响。",
    tuning_f_promote_min_speakers: "须经第二人认可",
    tuning_h_promote_min_speakers: "须得到两位不同用户的反应后才会投入使用，在此之前角色会继续观察。",
    tuning_f_promote_judge_enabled: "由角色自行判断反应无法确定的内容",
    tuning_h_promote_judge_enabled: "当反应相互矛盾、两种改法并存，或某条内容仅有认可作为依据时，角色会自行决定采用、搁置或继续观察。每次判断调用一次模型；若回答无法使用，会再请求一次。关闭后，这类内容将保持观察状态。",
    tuning_f_promote_observe_max_days: "观察内容的搁置期限（天）",
    tuning_h_promote_observe_max_days: "超过此天数仍未收到新反应的内容将被搁置。0 表示永不搁置。",
    tuning_f_agent_enabled: "回复消息",
    tuning_h_agent_enabled: "关闭后，角色仍保持与平台的连接，但不回复任何消息。",
    tuning_f_dashboard_enabled: "保留动态数据",
    tuning_h_dashboard_enabled: "为「{activity}」页提供数据：角色发言或保持沉默的原因，以及学到的内容。关闭后，「{activity}」页将为空，且无法在「{chat}」页或「{activity}」页中忘掉对话。",
    tuning_f_update_check_enabled: "检查更新",
    tuning_h_update_check_enabled: "每天向 pypi.org 查询一次是否有新版本，仅发送版本号。",
    tuning_f_proactive_interval_s: "主动发言检查间隔",
    tuning_h_proactive_interval_s: "角色每隔此时长检查一次是否主动发起对话。",
    tuning_f_proactive_min_silence_s: "群聊静默时长",
    tuning_h_proactive_min_silence_s: "群聊须保持静默达到此时长，角色才会主动发起对话。",
    tuning_f_proactive_cooldown_s: "群聊主动发言间隔",
    tuning_h_proactive_cooldown_s: "同一群聊中，两次主动发起对话的最短间隔。",
    tuning_f_proactive_prob: "每次检查主动发言的概率（群聊）",
    tuning_h_proactive_prob: "取值 0 至 1；0.25 表示约每四次检查发言一次。",
    tuning_f_proactive_dm_min_silence_s: "私聊静默时长",
    tuning_h_proactive_dm_min_silence_s: "私聊须保持静默达到此时长，角色才会主动发起对话。",
    tuning_f_proactive_dm_cooldown_s: "私聊主动发言间隔",
    tuning_h_proactive_dm_cooldown_s: "对同一用户两次主动发起私聊的最短间隔。",
    tuning_f_proactive_dm_prob: "每次检查主动发言的概率（私聊）",
    tuning_h_proactive_dm_prob: "取值 0 至 1。",
    tuning_f_chat_context_messages: "每个聊天保留的近期消息数",
    tuning_h_chat_context_messages: "用于回复和记忆整理的近期消息条数。每次回复最多读取最近 60 条。",
    tuning_f_memory_calls_per_day: "每日记忆整理调用次数",
    tuning_h_memory_calls_per_day: "所有聊天合计每天用于将对话整理为长期记忆的模型调用次数。设为 0 即关闭。",
    tuning_f_memory_tidy_every: "触发记忆整理的笔记数",
    tuning_h_memory_tidy_every: "某个聊天自上次整理以来在回复中记下的笔记达到此数量时，将对该聊天进行整理。设为 0 即关闭所有与记忆相关的模型调用。",
    tuning_f_memory_prompt_chars: "每次回复附带的记忆字数",
    tuning_h_memory_prompt_chars: "每次回复附带的记忆内容字数上限，包括此前对话的摘要、事实和事件。",
    tuning_f_memory_episodes_max: "每个聊天保留的事件数",
    tuning_h_memory_episodes_max: "某个聊天的事件超过此数量时，将移除最不重要的事件；移除的事件可在 30 天内恢复。",
    tuning_f_memory_keep_recent: "在本机保留近期消息",
    tuning_h_memory_keep_recent: "各聊天的近期消息在磁盘上保留 72 小时，重新启动后不会丢失。关闭后，近期消息仅在角色运行期间保留。",
    tuning_f_chat_followup_window_s: "接续回复时限",
    tuning_h_chat_followup_window_s: "角色回复后，此时限内的新消息均视为对角色的回复。",
    tuning_f_react_ttl_s: "回复的反应观察时长",
    tuning_h_react_ttl_s: "超过此时长后，不再读取他人对该条回复的反应。",
    tuning_f_react_max_pending: "每个聊天同时观察的回复数",
    tuning_h_react_max_pending: "角色同时观察其最近多少条回复收到的反应。",
    tuning_f_react_model: "反应判读模型",
    tuning_h_react_model: "留空即使用快速判断模型。",
    tuning_f_react_fix_window_s: "重新回答时限",
    tuning_h_react_fix_window_s: "一条回复被否定后，角色在此时限内的下一条回复视为重新回答。",
    tuning_f_react_elicit_delay_s: "询问前的等待时长",
    tuning_h_react_elicit_delay_s: "避免在角色自身的回复之后立即提问。",
    tuning_f_react_elicit_cooldown_s: "两次询问的最短间隔",
    tuning_h_react_elicit_cooldown_s: "在同一聊天中避免反复询问。",
    tuning_f_promote_min_events: "所需的一致反应次数",
    tuning_h_promote_min_events: "至少 2 次，以免一次误判即导致改动。",
    tuning_f_promote_min_strong: "其中明确纠正的次数",
    tuning_h_promote_min_strong: "至少 1 次：纠正中明确说明了应有的回复。",
    tuning_f_promote_evidence_max_age_days: "反应的有效期（天）",
    tuning_h_promote_evidence_max_age_days: "超过此天数的反应不再计入。0 表示不限。",
    tuning_f_promote_require_same_conversation: "仅合并同一聊天中的反应",
    tuning_h_promote_require_same_conversation: "避免单个用户在所有聊天中同时改变角色的行为。",
    tuning_f_promote_max_examples: "学到的示例上限",
    tuning_h_promote_max_examples: "0 表示不限。数量越多，每次回复需要检索的内容越多。",
    tuning_f_promote_max_feedback: "学到的纠正上限",
    tuning_h_promote_max_feedback: "0 表示不限。数量越多，每次回复需要检索的内容越多。",
    tuning_f_promote_judge_model: "角色自行判断所用的模型",
    tuning_h_promote_judge_model: "留空即使用反应判读模型。",
    tuning_f_promote_judge_interval_s: "角色判断的间隔",
    tuning_h_promote_judge_interval_s: "角色复查反应无法确定的内容的频率，至少 60。",
    tuning_f_promote_judge_batch: "每轮判断的数量上限",
    tuning_h_promote_judge_batch: "角色在一轮中最多判断的内容数量。每次判断调用一次模型；若回答无法使用，会再请求一次。",
    tuning_f_persona_version: "学习标签",
    tuning_h_persona_version: "在同一标签下修改人设，仍视为同一角色。使用新标签将重新开始学习；填回原标签即可恢复该标签下学到的内容。",
  },
});
(() => {
  const root = PA.$("tuning-root");
  const t = PA.t;
  const PRESETS = {
    rarely: [1500, 2700, 10800, 0.25, 14400, 86400, 0.2],
    sometimes: [1200, 1800, 5400, 0.35, 7200, 43200, 0.3],
    often: [900, 1200, 3600, 0.5, 3600, 21600, 0.4],
  };
  const PRESET_KEYS = [
    "PROACTIVE_INTERVAL_S", "PROACTIVE_MIN_SILENCE_S", "PROACTIVE_COOLDOWN_S", "PROACTIVE_PROB",
    "PROACTIVE_DM_MIN_SILENCE_S", "PROACTIVE_DM_COOLDOWN_S", "PROACTIVE_DM_PROB",
  ];
  const TZ = [];
  for (let h = -12; h <= 14; h++) TZ.push(h);
  TZ.push(-9.5, -3.5, 3.5, 4.5, 5.5, 5.75, 6.5, 8.75, 9.5, 10.5, 12.75);
  TZ.sort((a, b) => a - b);
  // Nodes whose text follows the language: [node, key, fields()].
  let texts = [];
  const inputs = {}; // key -> {field, input, wrap, shown, refresh}
  let data = null,
    dirty = false,
    busy = false,
    renameOk = false,
    errorCode = "";
  // View and feature names come from the page's own tables, so they always match.
  const names = () => ({
    chat: t("chat"),
    activity: t("activity"),
    platforms: t("platforms"),
    feature: t("proactiveTitle"),
    more: t("tuning_sec_more"),
    pick: t("tuning_pick"),
    me: t("tuning_me"),
  });
  const tell = (key, fields = {}) => t(key, { ...names(), ...fields });
  const say = (node, key, fields = () => ({})) => {
    texts.push([node, key, fields]);
    node.textContent = tell(key, fields());
    return node;
  };
  const prune = () => (texts = texts.filter(([node]) => node.isConnected || node === renameNote));
  const retell = () => {
    prune();
    for (const [node, key, fields] of texts) node.textContent = tell(key, fields());
    syncPick();
    if (errorCode && !error.hidden) error.textContent = errorText(errorCode);
    for (const item of Object.values(inputs)) if (item.refresh) item.refresh();
    if (data) {
      for (const item of Object.values(inputs))
        if (item.field.kind === "secret") {
          const hint = data.secrets[item.field.key];
          item.input.placeholder = hint ? t("tuning_key_saved", { hint }) : "";
        }
      showCooldowns();
    }
  };
  const el = (tag, cls, parent) => {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (parent) parent.append(node);
    return node;
  };
  const low = (key) => key.toLowerCase();
  const fieldName = (key) => t("tuning_f_" + low(key));
  const fmtTz = (hours) => {
    const sign = hours < 0 ? "-" : "+";
    const abs = Math.abs(hours);
    const m = Math.round((abs % 1) * 60);
    return `UTC${sign}${Math.floor(abs)}${m ? ":" + String(m).padStart(2, "0") : ""}`;
  };
  const platformOf = (id) => {
    const at = id.indexOf(":");
    return at > 0 ? id.slice(0, at) : "qq";
  };
  const idList = (text) =>
    text
      .replace(/，/g, ",")
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
  const note = (parent, key, fields) => say(el("p", "field-note", parent), key, fields);

  // ---- the card and its sections
  const card = el("div", "card tuning-card", root);
  say(el("h2", "", card), "tuning_title");
  note(card, "tuning_lead");
  const sections = {};
  for (const name of ["who", "talk", "models", "learning", "memory", "more"]) {
    const box = el("details", "tuning-section", card);
    box.dataset.section = name;
    say(el("summary", "", box), "tuning_sec_" + name);
    sections[name] = el("div", "tuning-body", box);
  }
  note(sections.more, "tuning_more_note");
  const error = el("div", "error", card);
  error.id = "tuning-error";
  error.setAttribute("role", "alert");
  error.hidden = true;
  const actions = el("div", "card-actions", card);
  const save = el("button", "primary", actions);
  save.type = "button";
  save.id = "tuning-save";
  say(save, "tuning_save");
  card.addEventListener("input", () => (dirty = true));
  card.addEventListener("change", () => (dirty = true));

  function addField(field, parent) {
    const wrap = el("div", "tuning-field", parent);
    wrap.dataset.key = field.key;
    const id = "tuning-" + low(field.key).replace(/_/g, "-");
    let input;
    if (field.kind === "bool" || field.kind === "choice") {
      const line = el("label", "check", wrap);
      input = el("input", "", line);
      input.type = "checkbox";
      say(el("span", "", line), "tuning_f_" + low(field.key));
    } else {
      const label = say(el("label", "", wrap), "tuning_f_" + low(field.key));
      label.htmlFor = id;
      if (field.kind === "tz") input = el("select", "", wrap);
      else {
        input = el("input", "", wrap);
        input.type = field.kind === "secret" ? "password" : "text";
        input.autocomplete = "off";
        input.spellcheck = false;
        if (field.kind === "int" || field.kind === "float") {
          input.inputMode = field.kind === "int" ? "numeric" : "decimal";
          input.placeholder = String(field.default);
        }
      }
    }
    input.id = id;
    const item = { field, input, wrap, shown: "" };
    inputs[field.key] = item;
    note(wrap, "tuning_h_" + low(field.key));
    return item;
  }
  const get = (key) => {
    const { field, input } = inputs[key];
    if (field.kind === "bool") return input.checked ? "true" : "false";
    if (field.kind === "choice") return input.checked ? "2" : "1";
    return input.value;
  };
  const set = (key, value) => {
    const { field, input } = inputs[key];
    if (field.kind === "bool") {
      const v = String(value).trim().toLowerCase();
      input.checked = ["1", "true", "yes", "on"].includes(v)
        ? true
        : ["0", "false", "no", "off"].includes(v)
          ? false
          : !!field.default;
    } else if (field.kind === "choice") input.checked = Number(value) >= 2;
    else input.value = value;
  };

  // ---- who: the owner's accounts and the allowlists, with a picker
  function restrictionNote(item) {
    const line = el("p", "field-note tuning-limit", item.wrap);
    item.refresh = () => {
      const platforms = [...new Set(idList(item.input.value).map(platformOf))];
      line.textContent = platforms.length
        ? t("tuning_restricted", { platforms: platforms.join(", ") })
        : t("tuning_unrestricted");
    };
    item.input.addEventListener("input", item.refresh);
  }
  const pickBox = el("div", "tuning-pick", sections.who);
  const pickButton = el("button", "secondary", pickBox);
  pickButton.type = "button";
  pickButton.id = "tuning-pick";
  say(pickButton, "tuning_pick");
  const pickList = el("div", "tuning-pick-list", pickBox);
  pickList.id = "tuning-pick-list";
  const has = (key, id) => idList(inputs[key].input.value).includes(id);
  function toggleId(key, id, on) {
    const item = inputs[key];
    const list = idList(item.input.value).filter((x) => x !== id);
    if (on) list.push(id);
    item.input.value = list.join(",");
    item.input.dispatchEvent(new Event("input", { bubbles: true }));
  }
  // One listener per list input (added in build) brings every shown row up to date.
  function syncPick() {
    if (!inputs.ADMIN_IDS) return;
    for (const row of pickList.querySelectorAll(".tuning-pick-row")) {
      const me = row.querySelector(".tuning-me");
      if (me) me.textContent = t(has("ADMIN_IDS", row.dataset.id) ? "tuning_not_me" : "tuning_me");
      row.querySelector("input[type=checkbox]").checked = has(row.dataset.list, row.dataset.id);
    }
  }
  function pickRow(chat, person, n) {
    const row = el("div", "tuning-pick-row", pickList);
    const key = person ? "ACCESS_DM_USERS" : "ACCESS_GROUPS";
    row.dataset.id = chat.id;
    row.dataset.list = key;
    el("span", "tuning-pick-id", row).textContent = chat.id;
    if (person) {
      const me = el("button", "quiet tuning-me", row);
      me.type = "button";
      me.id = "tuning-pick-me-" + n;
      me.addEventListener("click", () => toggleId("ADMIN_IDS", chat.id, !has("ADMIN_IDS", chat.id)));
    }
    const line = el("label", "check", row);
    const box = el("input", "", line);
    box.type = "checkbox";
    box.id = "tuning-pick-allow-" + n;
    say(el("span", "", line), person ? "tuning_may_dm" : "tuning_answer_here");
    box.addEventListener("change", () => toggleId(key, chat.id, box.checked));
  }
  pickButton.addEventListener("click", async () => {
    pickButton.disabled = true;
    pickButton.textContent = t("tuning_picking");
    error.hidden = true;
    try {
      const found = await PA.api("tuning/people");
      pickList.replaceChildren();
      prune();
      if (!found.running || found.off || !(found.people.length || found.groups.length)) {
        const line = note(pickList, !found.running ? "tuning_pick_not_running" : found.off ? "tuning_pick_off" : "tuning_pick_none");
        line.setAttribute("role", "status");
      } else {
        let n = 0;
        for (const [items, title, person] of [
          [found.people, "tuning_people", true],
          [found.groups, "tuning_groups", false],
        ]) {
          if (!items.length) continue;
          say(el("div", "tuning-pick-title", pickList), title);
          for (const chat of items) pickRow(chat, person, n++);
        }
        syncPick();
      }
    } catch (failure) {
      showError(failure.message);
    } finally {
      pickButton.disabled = false;
      pickButton.textContent = t("tuning_pick");
    }
  });

  // ---- talk: a speak-first preset over the seven timings, and the reply style card
  let presetSelect, cooldownLine, styleEmoji, styleMax;
  const styleSets = {};
  const effective = (key) => {
    const raw = inputs[key].input.value.trim();
    return raw === "" ? Number(inputs[key].field.default) : Number(raw);
  };
  function currentPreset() {
    for (const [name, values] of Object.entries(PRESETS))
      if (PRESET_KEYS.every((key, i) => effective(key) === values[i])) return name;
    return "custom";
  }
  function showCooldowns() {
    if (!cooldownLine) return;
    const hours = (key) => String(Math.round((effective(key) / 3600) * 10) / 10);
    cooldownLine.textContent = t("tuning_cooldowns", {
      group: hours("PROACTIVE_COOLDOWN_S"),
      dm: hours("PROACTIVE_DM_COOLDOWN_S"),
    });
  }
  function buildTalkExtras() {
    const wrap = el("div", "tuning-field", sections.talk);
    wrap.dataset.key = "preset";
    const label = say(el("label", "", wrap), "tuning_preset");
    presetSelect = el("select", "", wrap);
    presetSelect.id = "tuning-preset";
    label.htmlFor = presetSelect.id;
    for (const name of ["rarely", "sometimes", "often", "custom"]) {
      const option = say(el("option", "", presetSelect), "tuning_preset_" + name);
      option.value = name;
    }
    note(wrap, "tuning_preset_hint");
    cooldownLine = el("p", "field-note", wrap);
    cooldownLine.id = "tuning-cooldowns";
    presetSelect.addEventListener("change", () => {
      const values = PRESETS[presetSelect.value];
      if (values) PRESET_KEYS.forEach((key, i) => (inputs[key].input.value = String(values[i])));
      presetSelect.value = currentPreset();
      showCooldowns();
    });
    for (const key of PRESET_KEYS)
      inputs[key].input.addEventListener("input", () => {
        presetSelect.value = currentPreset();
        showCooldowns();
      });

    const style = el("div", "tuning-field tuning-style", sections.talk);
    style.dataset.key = "card";
    say(el("strong", "tuning-sub", style), "tuning_style");
    note(style, "tuning_style_hint");
    const emojiLine = el("label", "check", style);
    styleEmoji = el("input", "", emojiLine);
    styleEmoji.type = "checkbox";
    styleEmoji.id = "tuning-emoji";
    say(el("span", "", emojiLine), "tuning_emoji");
    const sets = el("div", "checks tuning-charsets", style);
    for (const name of ["ellipsis", "music", "arrows"]) {
      const line = el("label", "check", sets);
      styleSets[name] = el("input", "", line);
      styleSets[name].type = "checkbox";
      styleSets[name].id = "tuning-cs-" + name;
      say(el("span", "", line), "tuning_cs_" + name);
    }
    const maxLabel = say(el("label", "", style), "tuning_max_chars");
    styleMax = el("input", "", style);
    styleMax.id = "tuning-max-chars";
    styleMax.inputMode = "numeric";
    styleMax.autocomplete = "off";
    maxLabel.htmlFor = styleMax.id;
    note(style, "tuning_max_chars_hint", () => ({ min: data ? data.card.min : 50, max: data ? data.card.max : 800 }));
  }

  // ---- learning: start fresh
  let freshButton;
  function buildFresh() {
    const wrap = el("div", "tuning-field tuning-fresh", sections.learning);
    const line = note(wrap, "tuning_fresh_hint", () => ({
      label: (data && data.values.PERSONA_VERSION) || t("tuning_fresh_none"),
    }));
    line.id = "tuning-fresh-label";
    freshButton = el("button", "secondary", wrap);
    freshButton.type = "button";
    freshButton.id = "tuning-fresh";
    say(freshButton, "tuning_fresh");
    freshButton.addEventListener("click", async () => {
      if (!(await PA.ask(tell("tuning_fresh_ask"), t("tuning_fresh_yes")))) return;
      freshButton.disabled = true;
      freshButton.textContent = t("tuning_freshing");
      error.hidden = true;
      try {
        const result = await PA.api("tuning/fresh", {});
        data = result;
        set("PERSONA_VERSION", result.values.PERSONA_VERSION);
        inputs.PERSONA_VERSION.shown = result.values.PERSONA_VERSION;
        retell();
        PA.toast(t("tuning_fresh_done", { old: result.previous || t("tuning_fresh_none") }));
      } catch (failure) {
        showError(failure.message);
      } finally {
        freshButton.disabled = false;
        freshButton.textContent = t("tuning_fresh");
      }
    });
  }

  function build(fields) {
    if (Object.keys(inputs).length) return;
    for (const field of fields) {
      const item = addField(field, sections[field.section]);
      if (field.key === "ACCESS_GROUPS" || field.key === "ACCESS_DM_USERS") restrictionNote(item);
    }
    // Names, your accounts, the picker, then the allowlists it fills.
    sections.who.append(inputs.ADMIN_IDS.wrap, pickBox, inputs.ACCESS_GROUPS.wrap, inputs.ACCESS_DM_USERS.wrap);
    for (const key of ["ADMIN_IDS", "ACCESS_DM_USERS", "ACCESS_GROUPS"])
      inputs[key].input.addEventListener("input", syncPick);
    buildTalkExtras();
    buildFresh();
  }

  function fillTz() {
    const select = inputs.PERSONA_TZ_OFFSET_HOURS.input;
    const current = (data.values.PERSONA_TZ_OFFSET_HOURS || "").trim();
    const offsets = [...TZ];
    if (current && !offsets.includes(Number(current))) offsets.push(Number(current));
    offsets.sort((a, b) => a - b);
    select.replaceChildren();
    const auto = el("option", "", select);
    auto.value = "";
    say(auto, "tuning_tz_auto", () => ({ offset: fmtTz(data.tzAuto) }));
    for (const h of offsets) {
      const option = el("option", "", select);
      option.value = String(h);
      option.textContent = fmtTz(h);
    }
    select.value = current === "" ? "" : String(Number(current));
  }

  function fill() {
    build(data.fields);
    for (const item of Object.values(inputs)) {
      const { field, input } = item;
      if (field.kind === "tz") continue;
      if (field.kind === "secret") input.value = "";
      else set(field.key, data.values[field.key] ?? "");
      item.shown = get(field.key);
    }
    inputs.LLM_FALLBACK_BASE_URL.input.placeholder = data.llmBaseUrl || "";
    fillTz();
    inputs.PERSONA_TZ_OFFSET_HOURS.shown = inputs.PERSONA_TZ_OFFSET_HOURS.input.value;
    styleEmoji.checked = data.card.emoji;
    for (const [name, box] of Object.entries(styleSets)) box.checked = data.card.charsets.includes(name);
    styleMax.value = data.card.maxChars == null ? "" : String(data.card.maxChars);
    styleMax.placeholder = String(data.card.max);
    presetSelect.value = currentPreset();
    for (const node of card.querySelectorAll(".tuning-bad")) node.classList.remove("tuning-bad");
    retell();
    dirty = false;
  }
  const cardShown = () =>
    JSON.stringify([data.card.emoji, data.card.charsets, data.card.maxChars == null ? "" : String(data.card.maxChars)]);
  const chosenSets = () => Object.keys(styleSets).filter((n) => styleSets[n].checked);
  const cardNow = () => JSON.stringify([styleEmoji.checked, chosenSets(), styleMax.value.trim()]);

  // Kept as a code, so a shown error follows a language change.
  function errorText(code) {
    const [base, key] = String(code).split(":");
    if (base === "tuning_invalid" && key === "card")
      return t("tuning_err_card", { min: data ? data.card.min : 50, max: data ? data.card.max : 800 });
    if (base === "tuning_invalid" && inputs[key]) {
      const f = inputs[key].field;
      return f.kind === "ids"
        ? t("tuning_err_ids", { field: fieldName(key) })
        : (f.kind === "int" || f.kind === "float") && f.max != null
          ? t("tuning_err_range", { field: fieldName(key), min: f.min, max: f.max })
          : t("tuning_err_invalid", { field: fieldName(key) });
    }
    return tell(code);
  }
  function showError(code) {
    const [, key] = String(code).split(":");
    errorCode = String(code);
    const text = errorText(code);
    const fallback = /^tuning_(fallback|key_needed|https)/.test(code);
    const where =
      key === "card"
        ? card.querySelector('[data-key="card"]')
        : inputs[key]
          ? inputs[key].wrap
          : fallback && inputs.LLM_FALLBACK_MODEL
            ? inputs.LLM_FALLBACK_MODEL.wrap
            : null;
    if (where) {
      where.classList.add("tuning-bad");
      where.closest("details").open = true;
      const focus = where.querySelector("input, select");
      if (focus) focus.focus();
    }
    error.textContent = text;
    error.hidden = false;
  }

  save.addEventListener("click", async () => {
    if (busy || !data) return;
    const values = {};
    for (const [key, item] of Object.entries(inputs)) {
      const now = get(key);
      if (item.field.kind === "secret" ? now.trim() !== "" : now !== item.shown) values[key] = now;
    }
    const payload = { values };
    if (cardNow() !== cardShown())
      payload.card = { emoji: styleEmoji.checked, charsets: chosenSets(), maxChars: styleMax.value.trim() };
    if (!Object.keys(values).length && !payload.card) {
      PA.toast(t("tuning_nothing"));
      return;
    }
    if (values.AGENT_ENABLED === "false" && !(await PA.ask(t("tuning_ask_off"), t("tuning_ask_off_yes"))))
      return;
    busy = true;
    save.disabled = true;
    save.textContent = t("tuning_saving");
    error.hidden = true;
    for (const node of card.querySelectorAll(".tuning-bad")) node.classList.remove("tuning-bad");
    try {
      const result = await PA.api("tuning", payload);
      data = result;
      fill();
      const liveOnly = !payload.card && Object.keys(values).every((k) => k === "UPDATE_CHECK_ENABLED");
      PA.toast(
        t(
          !result.changed
            ? "tuning_nothing"
            : result.personaUpdated && result.restarted
              ? "tuning_saved_persona"
              : result.restarted
                ? "tuning_saved_restarted"
                : liveOnly
                  ? "tuning_saved"
                  : "tuning_saved_later",
        ),
      );
      PA.refresh().catch(() => {});
    } catch (failure) {
      showError(failure.message);
    } finally {
      busy = false;
      save.disabled = false;
      save.textContent = t("tuning_save");
    }
  });

  async function load() {
    try {
      data = await PA.api("tuning");
      fill();
      error.hidden = true;
    } catch (failure) {
      showError(failure.message);
    }
  }
  function visible() {
    const on = !!(PA.state && PA.state.configured && PA.view === "settings");
    root.hidden = !on;
    return on;
  }
  PA.onShow("settings", () => {
    if (visible() && !dirty) load();
  });
  PA.onState(() => visible());
  PA.onLanguage(retell);

  // ---- renaming: say what it does before it happens
  const renameNote = document.createElement("p");
  renameNote.className = "field-note tuning-rename";
  renameNote.id = "tuning-rename-note";
  renameNote.hidden = true;
  say(renameNote, "tuning_rename_note");
  const nameInput = PA.$("character-name");
  const renamed = () => {
    const st = PA.state;
    const typed = nameInput ? nameInput.value.trim() : "";
    return st && st.configured && st.name && typed && typed !== st.name ? typed : "";
  };
  if (nameInput) {
    nameInput.after(renameNote);
    const update = () => (renameNote.hidden = !renamed());
    nameInput.addEventListener("input", update);
    PA.onState(update);
  }
  // Captured on the document, so it runs before the page's own submit handler.
  document.addEventListener(
    "submit",
    async (event) => {
      if (!event.target || event.target.id !== "settings-form") return;
      if (renameOk) {
        renameOk = false;
        return;
      }
      const typed = renamed();
      if (!typed) return;
      event.preventDefault();
      event.stopImmediatePropagation();
      if (await PA.ask(t("tuning_rename_ask", { old: PA.state.name, new: typed }), t("tuning_rename_yes"))) {
        renameOk = true;
        event.target.requestSubmit();
      }
    },
    true,
  );
})();
