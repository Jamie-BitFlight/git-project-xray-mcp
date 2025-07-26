// JavaScript test file
import { readFile } from 'fs';
import axios from 'axios';

// Function declaration
function processData(data) {
    console.log('Processing data:', data);
    return data.map(item => item * 2);
}

// Arrow function
const fetchData = async (url) => {
    const response = await axios.get(url);
    return response.data;
};

// Class declaration
class DataService {
    constructor(apiUrl) {
        this.apiUrl = apiUrl;
    }
    
    async getData() {
        const data = await fetchData(this.apiUrl);
        return processData(data);
    }
    
    validateData(data) {
        return data && data.length > 0;
    }
}

// Function expression
const helper = function(x) {
    return x * 2;
};

// Export
export default DataService;
export { processData, fetchData };