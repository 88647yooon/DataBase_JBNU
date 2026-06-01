// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract BatchLogStore {
    struct BatchLog {
        string batchId;
        string batchHash;
        string previousHash;
        string createdAt;
    }

    BatchLog[] public batchLogs;

    event LogStored(
        string indexed batchId,
        string batchHash,
        string previousHash,
        string createdAt
    );

    function storeBatchLog(
        string memory _batchId,
        string memory _batchHash,
        string memory _previousHash,
        string memory _createdAt
    ) public {
        BatchLog memory newLog = BatchLog({
            batchId: _batchId,
            batchHash: _batchHash,
            previousHash: _previousHash,
            createdAt: _createdAt
        });

        batchLogs.push(newLog);
        
        emit LogStored(_batchId, _batchHash, _previousHash, _createdAt);
    }

    function getLogsCount() public view returns (uint256) {
        return batchLogs.length;
    }

    function getLog(uint256 index) public view returns (
        string memory batchId,
        string memory batchHash,
        string memory previousHash,
        string memory createdAt
    ) {
        require(index < batchLogs.length, "Index out of bounds");
        BatchLog memory log = batchLogs[index];
        return (log.batchId, log.batchHash, log.previousHash, log.createdAt);
    }
}