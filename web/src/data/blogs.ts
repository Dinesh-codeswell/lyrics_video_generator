export interface BlogPost {
  id: string;
  title: string;
  excerpt: string;
  content: string;
  date: string;
  category: string;
  readTime: string;
  featuredImage: string;
  contentImages?: string[];
}

export const blogs: BlogPost[] = [
  {
    id: 'mckinsey-interview-kit',
    title: 'McKinsey Interview Kit + Online Assessment Guide',
    excerpt: 'They don’t just hire the smartest person in the room — they hire the most prepared one.',
    date: 'May 24, 2026',
    category: 'Consulting',
    readTime: '8 min',
    featuredImage: '/blogs/images/McKinsey Blog ( Image 1).png',
    contentImages: [
      '/blogs/images/McKinsey blog ( image 2 ).png',
      '/blogs/images/McKinsey Logo.png'
    ],
    content: `
# Interview Kit + Online Assessment
They don’t just hire the smartest person in the room — they hire the most prepared one.

OA Prep  •  Case Frameworks  •  PEI Guide  •  Resume Templates  •  Offer Negotiation

“ I prepped for two months. Cases, frameworks, mock interviews. Then I walked into McKinsey’s OA and realised — it wasn’t even a test. It was a game. And I had no idea how to play it. ”

If that sounds like you, you’re not the problem. The process is. McKinsey doesn’t just test intelligence — it tests specific skills, in specific formats, at every stage.

### THE PROCESS AT A GLANCE
1. Application & resume screening
2. McKinsey Solve — gamified OA (the first real filter)
3. 1st-round interviews: 2 cases + PEI
4. Final-round: senior partner cases + PEI
5. Offer & negotiation

![McKinsey Process](/blogs/images/McKinsey blog ( image 2 ).png)

## SECTION 1 — THE MCKINSEY SOLVE ASSESSMENT
It’s not a test. It’s a game. That distinction is the whole problem. McKinsey’s OA uses Imbellus’s game-based platform. You’re not answering questions — you’re completing immersive simulations.

* **Ecosystem Management:** Balance species and food chains.
* **Plant Defence:** Set up defences using limited resources.
    `
  },
  {
    id: 'bcg-online-assessment',
    title: 'Nobody talks about what happens before the BCG case interview',
    excerpt: 'BCG’s Online Assessment isn’t a standard aptitude test. It’s a precision instrument designed to measure one thing: accurate thinking under pressure.',
    date: 'May 23, 2026',
    category: 'Consulting',
    readTime: '6 min',
    featuredImage: '/blogs/images/bcg oa round 1.png',
    contentImages: [
      '/blogs/images/bcg oa round 2.png'
    ],
    content: `
# Nobody talks about what happens before the case interview @BCG
There is a version of this story everyone knows. The BCG offer. The Bangalore office. The first project.

What doesn't get told is the unglamorous part. The part where you sit alone at 11pm working through data interpretation problems.

![BCG Round 1](/blogs/images/bcg oa round 1.png)

### What BCG's Round 1 OA actually involves
BCG's OA measures whether you can think accurately under pressure. 

1. **Data interpretation:** Multi-table datasets and business scenarios.
2. **Logical reasoning:** Pattern sequences and abstract reasoning.
3. **Numerical reasoning:** Ratios, percentages, and complex tables.

![BCG Round 2](/blogs/images/bcg oa round 2.png)
    `
  },
  {
    id: 'pwc-online-assessment',
    title: 'PwC careers look great on paper - but first, clear the OA',
    excerpt: 'The brand is strong, the roles are competitive, and the Online Assessment is the first real filter.',
    date: 'May 22, 2026',
    category: 'Careers',
    readTime: '5 min',
    featuredImage: '/blogs/images/pwc oa -img 2.png',
    contentImages: [
      '/blogs/images/pwc oa -characters.png'
    ],
    content: `
# PwC Careers: Getting past the first filter
“I finally applied, got to the OA stage, and blanked. I didn't even know what format to expect.”

### What you didn't know about Verbal Reasoning
You’re not being tested on comprehension. You’re being tested on whether you can evaluate a specific claim against a specific piece of text and nothing else.

![PwC Characters](/blogs/images/pwc oa -characters.png)
    `
  },
  {
    id: 'sql-handwritten-notes',
    title: 'The night before a SQL interview, you don’t want a 6-hour playlist',
    excerpt: 'Shar organized SQL notes, everything in one place, readable in two hours.',
    date: 'May 21, 2026',
    category: 'Technical',
    readTime: '4 min',
    featuredImage: '/blogs/images/sql hand written notes.png',
    content: `
# SQL Interview Prep
Rohan had his data analyst interview at a product startup in Bangalore. He didn't need a course. He needed SQL notes.

### What SQL interviews actually test
1. **DDL:** CREATE, ALTER, DROP, TRUNCATE.
2. **DML:** SELECT, INSERT, UPDATE, DELETE.
3. **JOINs & Aggregates:** The questions that separate good candidates from great ones.

![SQL Notes](/blogs/images/sql hand written notes.png)
    `
  },
  {
    id: 'verified-founder-hr-contact-sheet',
    title: 'STOP COLD EMAILING INTO THE VOID',
    excerpt: 'Why your outreach isn’t working — and the data behind what does.',
    date: 'May 20, 2026',
    category: 'Networking',
    readTime: '7 min',
    featuredImage: '/blogs/images/Verified Founder HR Contact Sheet Blog ( image 1 ).png',
    contentImages: [
      '/blogs/images/Verified Founder HR Contact Sheet Blog ( image 2 ).png',
      '/blogs/images/Verified Founder HR Contact Sheet Blog ( image 3 ).png'
    ],
    content: `
# The Verified Founder & HR Contact Sheet
Every week, thousands of candidates send out job applications. Most never hear back.

### The Access Gap
The average candidate spends 3–4 hours hunting for a single recruiter’s email. The data points toward a single root cause: access.

![HR Sheet 1](/blogs/images/Verified Founder HR Contact Sheet Blog ( image 1 ).png)
![HR Sheet 2](/blogs/images/Verified Founder HR Contact Sheet Blog ( image 2 ).png)
    `
  },
  {
    id: 'excel-financial-model-blog',
    title: 'Mastering Excel Financial Models',
    excerpt: 'Build robust, scalable financial models for consulting and finance roles.',
    date: 'May 19, 2026',
    category: 'Finance',
    readTime: '6 min',
    featuredImage: '/blogs/images/Excel_Financial_Model_Blog ( iamge 1 ).png',
    contentImages: [
      '/blogs/images/Excel_Financial_Model_Blog ( image 2 ).png'
    ],
    content: `
# Excel Financial Modeling
High-quality modeling is a core skill for any consulting or finance professional.

![Excel 1](/blogs/images/Excel_Financial_Model_Blog ( iamge 1 ).png)
![Excel 2](/blogs/images/Excel_Financial_Model_Blog ( image 2 ).png)
    `
  }
];
