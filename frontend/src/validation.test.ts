import {describe,expect,it} from 'vitest';
import {isValidAccount} from './validation';
describe('account IDs',()=>{it('accepts real alphanumeric IDs',()=>expect(isValidAccount('KKBK10000000')).toBe(true));it('rejects malformed IDs',()=>expect(isValidAccount('123')).toBe(false));});
