import { createClient } from '@supabase/supabase-js';
import dotenv from 'dotenv';

dotenv.config();

const supabaseUrl = process.env.SUPABASE_URL;
const supabaseServiceKey = process.env.SUPABASE_SERVICE_ROLE_KEY;

if (!supabaseServiceKey) {
  console.error('❌ SUPABASE_SERVICE_ROLE_KEY is required');
  process.exit(1);
}

const supabase = createClient(supabaseUrl, supabaseServiceKey);

async function checkStorage() {
  console.log('🔍 Checking Supabase Storage...\n');
  
  try {
    // List all files in worker-memories bucket
    const { data: files, error } = await supabase.storage
      .from('worker-memories')
      .list('', {
        limit: 100,
        offset: 0,
        search: 'CLAUDE.md'
      });
    
    if (error) {
      console.error('❌ Error listing files:', error);
      return;
    }
    
    console.log(`📁 Found ${files?.length || 0} CLAUDE.md files:\n`);
    
    if (files && files.length > 0) {
      for (const file of files) {
        console.log(`  - ${file.name}`);
        
        // Try to read the content
        const { data, error: downloadError } = await supabase.storage
          .from('worker-memories')
          .download(file.name);
        
        if (!downloadError && data) {
          const content = await data.text();
          console.log(`    Size: ${content.length} chars`);
          console.log(`    Preview: ${content.substring(0, 100)}...`);
        }
      }
    } else {
      console.log('  (No CLAUDE.md files found)');
    }
    
    // Check specific user's files
    const userId = '9f126de1-8f37-4635-bd33-b9e1fff262c1';
    console.log(`\n🔍 Checking files for user ${userId}:\n`);
    
    const { data: userFiles, error: userError } = await supabase.storage
      .from('worker-memories')
      .list(userId, {
        limit: 100,
        offset: 0
      });
    
    if (userError) {
      console.error('❌ Error listing user files:', userError);
      return;
    }
    
    if (userFiles && userFiles.length > 0) {
      for (const file of userFiles) {
        console.log(`  - ${userId}/${file.name}`);
      }
    } else {
      console.log('  (No files found for this user)');
    }
    
  } catch (error) {
    console.error('❌ Unexpected error:', error);
  }
}

checkStorage();
