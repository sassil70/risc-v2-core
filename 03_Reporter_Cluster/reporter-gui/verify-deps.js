
const colors = {
    reset: "\x1b[0m",
    green: "\x1b[32m",
    red: "\x1b[31m",
    cyan: "\x1b[36m"
};

const dependencies = [
    'next',
    'react',
    'react-dom',
    'puppeteer',
    'axios',
    'framer-motion',
    'lucide-react',
    'jspdf',
    'crypto-js'
];

console.log(`${colors.cyan}=== Neural Shadow: 4th Way Dependency Check ===${colors.reset}\n`);

let successCount = 0;

dependencies.forEach(dep => {
    try {
        require.resolve(dep);
        console.log(`${colors.green}✔ ${dep.padEnd(20)} [DETECTED]${colors.reset}`);
        successCount++;
    } catch (e) {
        console.log(`${colors.red}✘ ${dep.padEnd(20)} [MISSING]${colors.reset}`);
    }
});

console.log(`\n${colors.cyan}Result: ${successCount}/${dependencies.length} Operational${colors.reset}`);

if (successCount === dependencies.length) {
    process.exit(0);
} else {
    process.exit(1);
}
