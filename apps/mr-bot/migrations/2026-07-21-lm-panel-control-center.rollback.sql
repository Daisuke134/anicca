-- PANEL-0 rollback removes only additive control-center objects.
DROP FUNCTION IF EXISTS public.claim_lm_panel_oauth_state(text, text, text);
DROP TABLE IF EXISTS public.lm_panel_oauth_states;
DROP TABLE IF EXISTS public.lm_panel_command_receipts;
DROP TABLE IF EXISTS public.lm_panel_preferences;
