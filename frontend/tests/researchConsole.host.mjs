// Optional bounded handoff host, invoked only by owned fictional Python tool.
import {createServer} from 'vite';
const port=Number(process.argv[2]);if(!Number.isInteger(port)||port<1024)throw new Error('Owned port required');
const server=await createServer({envDir:false,server:{host:'localhost',port,strictPort:true},logLevel:'error'});await server.listen();
console.log('OWNED_READ_ONLY_CONSOLE_READY');
const timer=setTimeout(async()=>{await server.close();process.exit(0);},310000);
process.on('SIGTERM',async()=>{clearTimeout(timer);await server.close();process.exit(0);});
